import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Sum
from .models import (
    Project, DailyReport, Approval, RFI, NCR,
    MaterialRequest, MaterialItem, ChatRoom, ChatMessage
)


class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'WebSocket connected successfully!'
        }))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')

            if message_type == 'refresh_dashboard':
                stats = await self.get_dashboard_stats()
                await self.send(text_data=json.dumps({
                    'type': 'dashboard_update',
                    'stats': stats
                }))
        except Exception as e:
            print(f"Error in WebSocket receive: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    @database_sync_to_async
    def get_dashboard_stats(self):
        try:
            total_projects = Project.objects.count()
            active_projects = Project.objects.filter(status__in=['ACTIVE', 'ONGOING']).count()
            
            progress_values = []
            for p in Project.objects.all():
                latest_report = p.progress_reports.order_by('-report_date').first()
                if latest_report and latest_report.overall_progress:
                    progress_values.append(float(latest_report.overall_progress))
                else:
                    approved_daily = p.daily_reports.filter(status='APPROVED').order_by('-date').first()
                    if approved_daily and approved_daily.progress_percentage:
                        progress_values.append(float(approved_daily.progress_percentage))
            
            avg_progress = sum(progress_values) / len(progress_values) if progress_values else 0
            
            total_spent = Project.objects.aggregate(total=Sum('cost_summaries__actual'))['total'] or 0
            total_budget = Project.objects.aggregate(total=Sum('budget'))['total'] or 0
            
            open_rfi_count = RFI.objects.filter(status__in=['SUBMITTED', 'IN_REVIEW']).count()
            open_ncr_count = NCR.objects.filter(status__in=['OPEN', 'UNDER_REVIEW', 'CORRECTIVE_ACTION']).count()
            pending_approvals = Approval.objects.filter(status__in=['PENDING', 'REVIEWED']).count()
            material_requests_count = MaterialRequest.objects.count()
            
            low_stock_count = 0
            try:
                for item in MaterialItem.objects.all():
                    if hasattr(item, 'is_low_stock') and item.is_low_stock:
                        low_stock_count += 1
            except Exception as e:
                print(f"Error checking low stock: {e}")
            
            return {
                'total_projects': total_projects,
                'active_projects': active_projects,
                'avg_progress': round(avg_progress, 2),
                'total_spent': float(total_spent),
                'total_budget': float(total_budget),
                'open_rfi_count': open_rfi_count,
                'open_ncr_count': open_ncr_count,
                'pending_approvals': pending_approvals,
                'material_requests_count': material_requests_count,
                'low_stock_count': low_stock_count,
                'incident_count': 0
            }
        except Exception as e:
            print(f"Error getting dashboard stats: {e}")
            return {
                'total_projects': 0,
                'active_projects': 0,
                'avg_progress': 0,
                'total_spent': 0,
                'total_budget': 0,
                'open_rfi_count': 0,
                'open_ncr_count': 0,
                'pending_approvals': 0,
                'material_requests_count': 0,
                'low_stock_count': 0,
                'incident_count': 0
            }


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs'].get('room_id')
        self.room_group_name = f'chat_{self.room_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        sender = text_data_json['sender']
        room_id = text_data_json['room_id']
        
        await self.save_message(room_id, sender, message)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': sender,
                'timestamp': text_data_json.get('timestamp')
            }
        )

    async def chat_message(self, event):
        message = event['message']
        sender = event['sender']
        timestamp = event.get('timestamp')
        
        await self.send(text_data=json.dumps({
            'message': message,
            'sender': sender,
            'timestamp': timestamp
        }))

    @database_sync_to_async
    def save_message(self, room_id, sender_username, content):
        from django.contrib.auth.models import User
        try:
            room = ChatRoom.objects.get(id=room_id)
            sender = User.objects.get(username=sender_username)
            return ChatMessage.objects.create(
                room=room,
                sender=sender,
                content=content
            )
        except Exception as e:
            print(f"Error saving message: {e}")

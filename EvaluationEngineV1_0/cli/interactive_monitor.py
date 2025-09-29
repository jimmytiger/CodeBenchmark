"""
Interactive Monitor for Multi-Turn Evaluation

Provides real-time monitoring and interaction capabilities
for multi-turn evaluations.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import logging
import sys
import os

try:
    import websockets
    import aiohttp
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import Progress, TaskID
    from rich.layout import Layout
    from rich.text import Text
    RICH_AVAILABLE = True
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    WEBSOCKETS_AVAILABLE = False
    # Create mock classes for when rich is not available
    class Console:
        def print(self, *args, **kwargs):
            print(*args)
    
    class Progress:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def add_task(self, *args, **kwargs):
            return 0
        def update(self, *args, **kwargs):
            pass
    
    class Panel:
        def __init__(self, content, **kwargs):
            self.content = content
    
    class Table:
        def __init__(self, **kwargs):
            pass
        def add_column(self, *args, **kwargs):
            pass
        def add_row(self, *args, **kwargs):
            pass
    
    class Layout:
        def __init__(self, **kwargs):
            pass
        def split_column(self, *args):
            pass
        def split_row(self, *args):
            pass
        def __getitem__(self, key):
            return self
        def update(self, content):
            pass
    
    class Live:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

logger = logging.getLogger(__name__)


class InteractiveMonitor:
    """
    Interactive monitor for multi-turn evaluation progress.
    
    Implements requirement 9.2: Interactive mode for evaluation monitoring.
    """
    
    def __init__(self):
        self.console = Console()
        self.websocket = None
        self.session = None
        self.is_monitoring = False
        self.evaluations: Dict[str, Dict[str, Any]] = {}
        self.progress_tasks: Dict[str, TaskID] = {}
        self.event_handlers: Dict[str, Callable] = {}
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup event handlers for different message types."""
        self.event_handlers = {
            'connection_established': self._handle_connection_established,
            'evaluation_progress': self._handle_evaluation_progress,
            'turn_executed': self._handle_turn_executed,
            'evaluation_completed': self._handle_evaluation_completed,
            'safety_incident': self._handle_safety_incident,
            'system_event': self._handle_system_event,
            'error': self._handle_error
        }
    
    async def start_monitoring(self, host: str = 'localhost', port: int = 8000, 
                             token: Optional[str] = None):
        """
        Start interactive monitoring of evaluations.
        
        Args:
            host: API server host
            port: API server port
            token: Authentication token
        """
        if not WEBSOCKETS_AVAILABLE:
            self.console.print("WebSocket monitoring requires 'websockets' and 'aiohttp' packages")
            return
            
        try:
            self.console.print("Starting Interactive Monitor")
            self.console.print(f"Connecting to: ws://{host}:{port}/ws/multi-turn")
            
            # Create HTTP session for API calls
            self.session = aiohttp.ClientSession()
            
            # Connect to WebSocket
            headers = {}
            if token:
                headers['Authorization'] = f'Bearer {token}'
            
            websocket_url = f"ws://{host}:{port}/ws/multi-turn"
            if token:
                websocket_url += f"?token={token}"
            
            async with websockets.connect(websocket_url, extra_headers=headers) as websocket:
                self.websocket = websocket
                self.is_monitoring = True
                
                # Start monitoring tasks
                await asyncio.gather(
                    self._websocket_listener(),
                    self._display_dashboard(),
                    self._handle_user_input()
                )
                
        except Exception as e:
            if WEBSOCKETS_AVAILABLE and hasattr(websockets.exceptions, 'ConnectionClosed') and isinstance(e, websockets.exceptions.ConnectionClosed):
                self.console.print("WebSocket connection closed")
            else:
                self.console.print(f"Error: {str(e)}")
        finally:
            self.is_monitoring = False
            if hasattr(self, 'session') and self.session:
                await self.session.close()
    
    async def start_local_monitoring(self):
        """Start monitoring for local evaluations (without WebSocket)."""
        self.console.print("[bold green]Starting Local Monitor[/bold green]")
        self.is_monitoring = True
        
        try:
            await self._display_local_dashboard()
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Monitoring stopped by user[/yellow]")
        finally:
            self.is_monitoring = False
    
    async def _websocket_listener(self):
        """Listen for WebSocket messages."""
        try:
            while self.is_monitoring:
                message = await self.websocket.recv()
                await self._handle_websocket_message(message)
        except websockets.exceptions.ConnectionClosed:
            self.is_monitoring = False
        except Exception as e:
            logger.error(f"WebSocket listener error: {str(e)}")
    
    async def _handle_websocket_message(self, message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type in self.event_handlers:
                await self.event_handlers[message_type](data)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON message: {message}")
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
    
    async def _display_dashboard(self):
        """Display real-time dashboard."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="evaluations"),
            Layout(name="details")
        )
        
        with Live(layout, refresh_per_second=2, screen=True):
            while self.is_monitoring:
                # Update header
                layout["header"].update(self._create_header_panel())
                
                # Update evaluations list
                layout["evaluations"].update(self._create_evaluations_panel())
                
                # Update details
                layout["details"].update(self._create_details_panel())
                
                # Update footer
                layout["footer"].update(self._create_footer_panel())
                
                await asyncio.sleep(0.5)
    
    async def _display_local_dashboard(self):
        """Display dashboard for local monitoring."""
        with Progress() as progress:
            # Add progress bars for tasks
            task1 = progress.add_task("[green]Task 1", total=100)
            task2 = progress.add_task("[blue]Task 2", total=100)
            
            # Simulate progress
            for i in range(100):
                progress.update(task1, advance=1)
                if i > 20:
                    progress.update(task2, advance=1)
                
                await asyncio.sleep(0.1)
                
                if not self.is_monitoring:
                    break
    
    def _create_header_panel(self) -> Panel:
        """Create header panel."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        active_count = len([e for e in self.evaluations.values() if e.get('status') == 'running'])
        
        header_text = f"Multi-Turn Evaluation Monitor | {current_time} | Active: {active_count}"
        return Panel(header_text, style="bold blue")
    
    def _create_evaluations_panel(self) -> Panel:
        """Create evaluations list panel."""
        if not self.evaluations:
            return Panel("No evaluations found", title="Evaluations")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim", width=20)
        table.add_column("Model", width=15)
        table.add_column("Status", width=12)
        table.add_column("Progress", width=15)
        table.add_column("Tasks", width=10)
        
        for eval_id, eval_data in self.evaluations.items():
            status = eval_data.get('status', 'unknown')
            progress = eval_data.get('progress', 0.0)
            completed_tasks = eval_data.get('completed_tasks', 0)
            total_tasks = eval_data.get('total_tasks', 0)
            
            # Color code status
            if status == 'running':
                status_text = f"[green]{status}[/green]"
            elif status == 'completed':
                status_text = f"[blue]{status}[/blue]"
            elif status == 'failed':
                status_text = f"[red]{status}[/red]"
            else:
                status_text = status
            
            progress_text = f"{progress:.1%}"
            tasks_text = f"{completed_tasks}/{total_tasks}"
            
            table.add_row(
                eval_id[:18] + "..." if len(eval_id) > 20 else eval_id,
                eval_data.get('model_id', 'unknown'),
                status_text,
                progress_text,
                tasks_text
            )
        
        return Panel(table, title="Active Evaluations")
    
    def _create_details_panel(self) -> Panel:
        """Create details panel."""
        if not self.evaluations:
            return Panel("Select an evaluation to view details", title="Details")
        
        # Show details for the most recent evaluation
        latest_eval = max(self.evaluations.values(), 
                         key=lambda x: x.get('created_at', datetime.min))
        
        details_text = []
        details_text.append(f"Evaluation ID: {latest_eval.get('evaluation_id', 'unknown')}")
        details_text.append(f"Model: {latest_eval.get('model_id', 'unknown')}")
        details_text.append(f"Status: {latest_eval.get('status', 'unknown')}")
        details_text.append(f"Current Task: {latest_eval.get('current_task', 'none')}")
        details_text.append(f"Current Turn: {latest_eval.get('current_turn', 0)}")
        details_text.append(f"Safety Incidents: {latest_eval.get('safety_incidents', 0)}")
        details_text.append(f"Total Turns: {latest_eval.get('total_turns_executed', 0)}")
        
        if 'start_time' in latest_eval:
            elapsed = datetime.now() - latest_eval['start_time']
            details_text.append(f"Elapsed Time: {str(elapsed).split('.')[0]}")
        
        return Panel("\n".join(details_text), title="Evaluation Details")
    
    def _create_footer_panel(self) -> Panel:
        """Create footer panel."""
        footer_text = "Press 'q' to quit | 'r' to refresh | 's' to subscribe to evaluation"
        return Panel(footer_text, style="dim")
    
    async def _handle_user_input(self):
        """Handle user input for interactive commands."""
        # This would implement keyboard input handling
        # For now, just wait for monitoring to stop
        while self.is_monitoring:
            await asyncio.sleep(1)
    
    # Event handlers
    
    async def _handle_connection_established(self, data: Dict[str, Any]):
        """Handle connection established event."""
        self.console.print("[green]✓ WebSocket connection established[/green]")
        
        # Subscribe to system events
        subscribe_message = {
            "type": "subscribe",
            "subscription_type": "system"
        }
        await self.websocket.send(json.dumps(subscribe_message))
    
    async def _handle_evaluation_progress(self, data: Dict[str, Any]):
        """Handle evaluation progress event."""
        evaluation_id = data.get('evaluation_id')
        progress_data = data.get('data', {})
        
        if evaluation_id not in self.evaluations:
            self.evaluations[evaluation_id] = {'evaluation_id': evaluation_id}
        
        self.evaluations[evaluation_id].update(progress_data)
        
        # Log progress update
        progress = progress_data.get('progress', 0.0)
        current_task = progress_data.get('current_task', 'unknown')
        self.console.print(f"[blue]Progress Update[/blue] {evaluation_id}: {progress:.1%} - {current_task}")
    
    async def _handle_turn_executed(self, data: Dict[str, Any]):
        """Handle turn executed event."""
        evaluation_id = data.get('evaluation_id')
        turn_data = data.get('data', {})
        
        turn_number = turn_data.get('turn_number', 0)
        action_type = turn_data.get('action', {}).get('type', 'unknown')
        reward = turn_data.get('reward', 0.0)
        
        self.console.print(f"[yellow]Turn Executed[/yellow] {evaluation_id}: Turn {turn_number} - {action_type} (reward: {reward})")
    
    async def _handle_evaluation_completed(self, data: Dict[str, Any]):
        """Handle evaluation completed event."""
        evaluation_id = data.get('evaluation_id')
        results_data = data.get('data', {})
        
        success_rate = results_data.get('overall_success_rate', 0.0)
        total_turns = results_data.get('total_turns_executed', 0)
        
        self.console.print(f"[green]✓ Evaluation Completed[/green] {evaluation_id}: {success_rate:.1%} success, {total_turns} turns")
        
        # Update evaluation status
        if evaluation_id in self.evaluations:
            self.evaluations[evaluation_id]['status'] = 'completed'
            self.evaluations[evaluation_id]['progress'] = 1.0
    
    async def _handle_safety_incident(self, data: Dict[str, Any]):
        """Handle safety incident event."""
        evaluation_id = data.get('evaluation_id')
        incident_data = data.get('data', {})
        
        incident_type = incident_data.get('incident_type', 'unknown')
        severity = incident_data.get('severity', 'unknown')
        
        self.console.print(f"[red]⚠ Safety Incident[/red] {evaluation_id}: {incident_type} ({severity})")
        
        # Update safety incident count
        if evaluation_id in self.evaluations:
            current_incidents = self.evaluations[evaluation_id].get('safety_incidents', 0)
            self.evaluations[evaluation_id]['safety_incidents'] = current_incidents + 1
    
    async def _handle_system_event(self, data: Dict[str, Any]):
        """Handle system event."""
        event_data = data.get('data', {})
        event_type = event_data.get('event_type', 'unknown')
        message = event_data.get('message', 'No message')
        
        self.console.print(f"[cyan]System Event[/cyan] {event_type}: {message}")
    
    async def _handle_error(self, data: Dict[str, Any]):
        """Handle error event."""
        error_type = data.get('error', 'unknown')
        message = data.get('message', 'No message')
        
        self.console.print(f"[red]Error[/red] {error_type}: {message}")
    
    # API interaction methods
    
    async def get_evaluation_status(self, evaluation_id: str, host: str = 'localhost', 
                                  port: int = 8000, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get evaluation status from API."""
        try:
            headers = {}
            if token:
                headers['Authorization'] = f'Bearer {token}'
            
            url = f"http://{host}:{port}/multi-turn/evaluations/{evaluation_id}/status"
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting evaluation status: {str(e)}")
            return None
    
    async def list_evaluations(self, host: str = 'localhost', port: int = 8000, 
                             token: Optional[str] = None) -> List[Dict[str, Any]]:
        """List evaluations from API."""
        try:
            headers = {}
            if token:
                headers['Authorization'] = f'Bearer {token}'
            
            url = f"http://{host}:{port}/multi-turn/evaluations"
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('items', [])
                else:
                    logger.error(f"API error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error listing evaluations: {str(e)}")
            return []
    
    async def subscribe_to_evaluation(self, evaluation_id: str):
        """Subscribe to specific evaluation updates."""
        if self.websocket:
            subscribe_message = {
                "type": "subscribe",
                "subscription_type": "evaluation",
                "evaluation_id": evaluation_id
            }
            await self.websocket.send(json.dumps(subscribe_message))
            self.console.print(f"[green]Subscribed to evaluation: {evaluation_id}[/green]")
    
    def display_evaluation_summary(self, evaluation_data: Dict[str, Any]):
        """Display evaluation summary."""
        table = Table(title="Evaluation Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Evaluation ID", evaluation_data.get('evaluation_id', 'unknown'))
        table.add_row("Model", evaluation_data.get('model_id', 'unknown'))
        table.add_row("Status", evaluation_data.get('status', 'unknown'))
        table.add_row("Progress", f"{evaluation_data.get('progress', 0.0):.1%}")
        table.add_row("Completed Tasks", str(evaluation_data.get('completed_tasks', 0)))
        table.add_row("Total Tasks", str(evaluation_data.get('total_tasks', 0)))
        table.add_row("Safety Incidents", str(evaluation_data.get('safety_incidents', 0)))
        table.add_row("Total Turns", str(evaluation_data.get('total_turns_executed', 0)))
        
        self.console.print(table)
    
    def display_turn_details(self, turn_data: Dict[str, Any]):
        """Display turn execution details."""
        panel_content = []
        panel_content.append(f"Turn Number: {turn_data.get('turn_number', 0)}")
        panel_content.append(f"Action Type: {turn_data.get('action', {}).get('type', 'unknown')}")
        panel_content.append(f"Reward: {turn_data.get('reward', 0.0)}")
        panel_content.append(f"Done: {turn_data.get('done', False)}")
        
        if 'observation' in turn_data:
            obs = turn_data['observation']
            if 'stdout' in obs:
                panel_content.append(f"Output: {obs['stdout'][:100]}...")
        
        panel = Panel("\n".join(panel_content), title="Turn Details")
        self.console.print(panel)
"""Event generator for testing and demo purposes."""

import asyncio
import random
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.models.events import EventType

logger = get_logger(__name__)

# Sample data for realistic event generation
SAMPLE_USERS = [f"user_{i:04d}" for i in range(1, 101)]
SAMPLE_SESSIONS = [f"sess_{uuid.uuid4().hex[:8]}" for _ in range(50)]
SAMPLE_PAGES = [
    "/", "/home", "/products", "/products/1", "/products/2",
    "/cart", "/checkout", "/account", "/settings", "/help",
    "/blog", "/blog/post-1", "/blog/post-2", "/about", "/contact",
]
SAMPLE_ELEMENTS = [
    "navbar_logo", "search_input", "add_to_cart_btn", "checkout_btn",
    "signup_btn", "login_btn", "subscribe_btn", "share_btn",
    "product_image", "product_title", "filter_dropdown", "sort_btn",
]
SAMPLE_REFERRERS = [
    "google.com", "facebook.com", "twitter.com", "linkedin.com",
    "reddit.com", "direct", "email", "instagram.com",
]
SAMPLE_BROWSERS = [
    "Chrome/120.0", "Firefox/121.0", "Safari/17.0",
    "Edge/120.0", "Opera/105.0",
]
SAMPLE_DEVICES = ["desktop", "mobile", "tablet"]
SAMPLE_OS = ["Windows 11", "macOS 14", "iOS 17", "Android 14", "Linux"]
ERROR_MESSAGES = [
    "Network timeout",
    "API rate limit exceeded",
    "Invalid authentication token",
    "Resource not found",
    "Internal server error",
    "Database connection failed",
]


class EventGenerator:
    """Generates realistic sample events for testing."""

    def __init__(self, user_count: int = 100):
        self.users = SAMPLE_USERS[:user_count]
        self.sessions: Dict[str, str] = {}  # user_id -> session_id

    def generate_event(
        self,
        event_type: Optional[EventType] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a single random event."""
        if event_type is None:
            # Weighted random selection
            weights = {
                EventType.PAGE_VIEW: 0.35,
                EventType.CLICK: 0.30,
                EventType.USER_ACTION: 0.15,
                EventType.FORM_SUBMIT: 0.08,
                EventType.PURCHASE: 0.05,
                EventType.ERROR: 0.05,
                EventType.CUSTOM: 0.02,
            }
            event_type = random.choices(
                list(weights.keys()),
                weights=list(weights.values()),
            )[0]

        if user_id is None:
            user_id = random.choice(self.users)

        # Get or create session for user
        if user_id not in self.sessions or random.random() < 0.1:
            self.sessions[user_id] = f"sess_{uuid.uuid4().hex[:8]}"
        session_id = self.sessions[user_id]

        # Generate event-specific payload
        payload = self._generate_payload(event_type)
        metadata = self._generate_metadata()

        return {
            "id": str(uuid.uuid4()),
            "event_type": event_type.value,
            "user_id": user_id,
            "session_id": session_id,
            "payload": payload,
            "metadata": metadata,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _generate_payload(self, event_type: EventType) -> Dict[str, Any]:
        """Generate event-type specific payload."""
        if event_type == EventType.PAGE_VIEW:
            return {
                "page": random.choice(SAMPLE_PAGES),
                "referrer": random.choice(SAMPLE_REFERRERS),
                "load_time_ms": random.randint(100, 3000),
            }

        elif event_type == EventType.CLICK:
            return {
                "element": random.choice(SAMPLE_ELEMENTS),
                "page": random.choice(SAMPLE_PAGES),
                "x": random.randint(0, 1920),
                "y": random.randint(0, 1080),
            }

        elif event_type == EventType.USER_ACTION:
            actions = ["scroll", "hover", "focus", "blur", "copy", "paste"]
            return {
                "action": random.choice(actions),
                "target": random.choice(SAMPLE_ELEMENTS),
                "page": random.choice(SAMPLE_PAGES),
            }

        elif event_type == EventType.FORM_SUBMIT:
            forms = ["login", "signup", "contact", "search", "newsletter"]
            return {
                "form_id": random.choice(forms),
                "success": random.random() > 0.1,
                "validation_errors": random.randint(0, 3) if random.random() < 0.2 else 0,
            }

        elif event_type == EventType.PURCHASE:
            return {
                "product_id": f"prod_{random.randint(1, 1000):04d}",
                "quantity": random.randint(1, 5),
                "price": round(random.uniform(9.99, 999.99), 2),
                "currency": "USD",
                "payment_method": random.choice(["credit_card", "paypal", "apple_pay"]),
            }

        elif event_type == EventType.ERROR:
            return {
                "error_message": random.choice(ERROR_MESSAGES),
                "error_code": random.choice([400, 401, 403, 404, 500, 502, 503]),
                "stack_trace": f"Error at line {random.randint(1, 500)}",
                "page": random.choice(SAMPLE_PAGES),
            }

        else:  # CUSTOM
            return {
                "custom_key": f"value_{random.randint(1, 100)}",
                "data": {"nested": True, "count": random.randint(1, 10)},
            }

    def _generate_metadata(self) -> Dict[str, Any]:
        """Generate common metadata for events."""
        return {
            "browser": random.choice(SAMPLE_BROWSERS),
            "device": random.choice(SAMPLE_DEVICES),
            "os": random.choice(SAMPLE_OS),
            "screen_width": random.choice([1366, 1920, 2560, 375, 414, 768]),
            "screen_height": random.choice([768, 1080, 1440, 667, 896, 1024]),
            "language": random.choice(["en-US", "en-GB", "es-ES", "fr-FR", "de-DE"]),
            "timezone": random.choice(["America/New_York", "Europe/London", "Asia/Tokyo"]),
        }

    async def generate_events(
        self,
        count: int,
        event_type: Optional[EventType] = None,
        delay_ms: int = 0,
    ) -> List[Dict[str, Any]]:
        """Generate multiple events with optional delay."""
        events = []

        for _ in range(count):
            event = self.generate_event(event_type=event_type)
            events.append(event)

            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)

        logger.info(f"Generated {count} events")
        return events

    def generate_events_sync(
        self,
        count: int,
        event_type: Optional[EventType] = None,
    ) -> List[Dict[str, Any]]:
        """Generate multiple events synchronously."""
        return [self.generate_event(event_type=event_type) for _ in range(count)]

from dataclasses import dataclass
from typing import Optional


@dataclass
class RegisterDeviceTokenRequest:
    user_id: str
    token: str
    device_type: str
    device_name: Optional[str] = None

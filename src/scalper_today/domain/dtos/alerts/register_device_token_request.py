from dataclasses import dataclass


@dataclass
class RegisterDeviceTokenRequest:
    user_id: str
    token: str
    device_type: str
    device_name: str | None = None

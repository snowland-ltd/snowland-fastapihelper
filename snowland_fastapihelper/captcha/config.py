"""Timing configuration for captcha codes."""
from dataclasses import dataclass

DEFAULT_EXPIRE_SECONDS = 300
DEFAULT_RETAIN_SECONDS = 900
DEFAULT_CODE_LENGTH = 6


@dataclass
class CaptchaConfig:
    """Timing settings for captcha codes.

    Attributes:
        expire_seconds: validity window of a code. Verification succeeds only
            within this window after the code is generated.
        retain_seconds: how long the code record is kept in the cache. It must be
            >= ``expire_seconds``; the extra time after expiry lets the service
            tell "this code expired" from "no code was ever generated".
        code_length: number of digits in a generated code.
    """

    expire_seconds: int = DEFAULT_EXPIRE_SECONDS
    retain_seconds: int = DEFAULT_RETAIN_SECONDS
    code_length: int = DEFAULT_CODE_LENGTH

    def __post_init__(self) -> None:
        if self.expire_seconds <= 0:
            raise ValueError("expire_seconds must be positive")
        if self.retain_seconds < self.expire_seconds:
            raise ValueError("retain_seconds must be >= expire_seconds")
        if self.code_length <= 0:
            raise ValueError("code_length must be positive")

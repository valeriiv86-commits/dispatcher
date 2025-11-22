$ErrorActionPreference = 'Stop'
$path = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'order.py'
$newContent = @'
from pydantic import BaseModel
from typing import Optional


class OrderBase(BaseModel):
    client_name: str
    client_phone: str
    from_address: str
    to_address: str
    price: float = 0
    totalPrice: Optional[float] = None
    comment: Optional[str] = ""
    performer: Optional[str] = ""
    status: Optional[str] = "new"


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    performer: Optional[str] = None
    comment: Optional[str] = None
    price: Optional[float] = None
    totalPrice: Optional[float] = None
'@
$current = if (Test-Path $path) { Get-Content -Raw $path } else { '' }
if ($current -ne $newContent) {
    $newContent | Set-Content -Path $path -Encoding UTF8
    Write-Host "[UPDATE] order.py refreshed"
} else {
    Write-Host "[SKIP] order.py already up to date"
}

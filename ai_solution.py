```python
from typing import Optional
from datetime import datetime, timedelta
from asyncio import wait, gather

class DodgeRolling:
    def __init__(self):
        self._dodge_rolling_active = False
        self._dodge_rolling_until = None

    async def dodge_roll(self):
        if self._dodge_rolling_active:
            await self.bot.send_message(
                message_thread_id=self.message_thread_id,
                message="You're already dodging! You can roll again in 10 seconds."
            )
            return
        self._dodge_rolling_active = True
        self._dodge_rolling_until = datetime.now() + timedelta(seconds=10)
        await self.bot.send_message(
            message_thread_id=self.message_thread_id,
            message="You've rolled to dodge! You won't take damage for the next 10 seconds."
        )
        await gather(wait(self._dodge_rolling_until))

    @property
    def dodge_rolling_active(self) -> bool:
        return self._dodge_rolling_active

    @property
    def dodge_rolling_until(self) -> Optional[datetime]:
        return self._dodge_rolling_until

    async def take_damage(self, damage: int) -> int:
        if self._dodge_rolling_active and datetime.now() < self._dodge_rolling_until:
            self._dodge_rolling_active = False
            self._dodge_rolling_until = None
            return 0
        return damage

    async def reset(self):
        self._dodge_rolling_active = False
        self._dodge_rolling_until = None
```
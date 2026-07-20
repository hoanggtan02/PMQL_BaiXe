import sys

with open("src/pmql/ui/app.py", encoding="utf-8") as f:
    content = f.read()

OLD_CREATE = "async def _create_fee_rule(settings: Settings, name: str, vehicle_type: str, block_minutes: int, price_per_block: int, free_minutes: int, night_surcharge: int, day_max: int | None) -> None:"
NEW_CREATE = "async def _create_fee_rule(settings: Settings, name: str, vehicle_type: str, block_minutes: int, price_per_block: int, free_minutes: int, night_surcharge: int, day_max: int | None, is_active: bool = True) -> None:"

OLD_CREATE_CALL = "FeeRuleInput(settings.branch_id, name, vehicle_type, free_minutes, block_minutes, price_per_block, day_max))"
NEW_CREATE_CALL = "FeeRuleInput(settings.branch_id, name, vehicle_type, free_minutes, block_minutes, price_per_block, day_max, is_active))"

OLD_UPDATE = "async def _update_fee_rule(settings: Settings, rule_id: str, name: str, vehicle_type: str, block_minutes: int, price_per_block: int, free_minutes: int, night_surcharge: int, day_max: int | None) -> None:"
NEW_UPDATE = "async def _update_fee_rule(settings: Settings, rule_id: str, name: str, vehicle_type: str, block_minutes: int, price_per_block: int, free_minutes: int, night_surcharge: int, day_max: int | None, is_active: bool = True) -> None:"

content = content.replace(OLD_CREATE, NEW_CREATE)
content = content.replace(OLD_UPDATE, NEW_UPDATE)

# Replace the first two instances of the FeeRuleInput call
first_call = content.find(OLD_CREATE_CALL)
if first_call != -1:
    content = content[:first_call] + NEW_CREATE_CALL + content[first_call + len(OLD_CREATE_CALL):]
second_call = content.find(OLD_CREATE_CALL, first_call + 1)
if second_call != -1:
    content = content[:second_call] + NEW_CREATE_CALL + content[second_call + len(OLD_CREATE_CALL):]

with open("src/pmql/ui/app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patch _create_fee_rule and _update_fee_rule done!")

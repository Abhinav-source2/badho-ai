from app.core.state import get_session
from app.core.budget import is_over_budget, record_cost

sid = "budget-test-999"

print("Over budget before:", is_over_budget(sid))

record_cost(sid, 0.09)
print("Over budget at 0.09:", is_over_budget(sid))

record_cost(sid, 0.02)
print("Over budget at 0.11:", is_over_budget(sid))
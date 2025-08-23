# Move simulate_event_processing to Test Helpers

## Overview
Move the `simulate_event_processing` method from `services/common/idempotency/idempotency_service.py` to an appropriate test helper file, as it's purely for testing purposes and clutters the production service.

## Current State
- `simulate_event_processing` method exists in `IdempotencyService` class
- Method is only used in test files for testing idempotency configuration
- Method has no production business logic value
- Clutters the main service class

## Analysis Results (Phase 1 Complete)
- **Current Usage**: Method is used in 2 test files:
  - `services/common/tests/test_event_driven_architecture_integration.py` (lines 67, 505)
  - `services/common/tests/test_idempotency.py` (line 459)
- **Helper Location**: Best approach is `services/common/tests/helpers/idempotency_test_helpers.py`
- **Implementation**: Should be a standalone function for maximum reusability
- **Dependencies**: Requires `IdempotencyKeyGenerator`, `IdempotencyKeyValidator`, `IdempotencyStrategy`

## Target State
- `simulate_event_processing` moved to dedicated test helper file
- `IdempotencyService` focused purely on production idempotency logic
- Test utilities properly organized in test infrastructure
- Cleaner separation between production and test code

## Migration Checklist

### Phase 1: Analysis and Planning
- [x] Audit current usage of `simulate_event_processing` across test files
- [x] Identify all test files that import or use this method
- [x] Determine best location for the test helper (helpers vs utils vs conftest)
- [x] Plan the new test helper structure
- [x] Review if method should be a standalone function or part of a helper class

### Phase 2: Create Test Helper Structure
- [x] Create `services/common/tests/helpers/` directory if it doesn't exist
- [x] Create `services/common/tests/helpers/idempotency_test_helpers.py`
- [x] Move `simulate_event_processing` logic to the new helper file
- [x] Ensure helper has proper imports and dependencies
- [x] Add appropriate docstrings and type hints

### Phase 3: Update Test Helper Implementation
- [x] Extract the simulation logic from `IdempotencyService`
- [x] Adapt the method to work as a standalone function or helper method
- [x] Ensure all dependencies are properly imported
- [x] Add any missing imports that were previously available in the service
- [x] Test the helper function independently

### Phase 4: Update Test Files
- [x] Update `services/common/tests/test_idempotency.py` to use new helper
- [x] Update `services/common/tests/test_event_driven_architecture_integration.py` to use new helper
- [x] Update any other test files that use the simulation method
- [x] Ensure all tests still pass with the new helper
- [x] Update import statements in test files

### Phase 5: Clean Up IdempotencyService
- [x] Remove `simulate_event_processing` method from `IdempotencyService`
- [x] Remove any unused imports related to simulation
- [x] Ensure service class is focused on production logic
- [x] Update service documentation if needed
- [x] Verify service still works correctly

### Phase 6: Validation and Testing
- [ ] Run all idempotency-related tests to ensure they pass
- [ ] Run broader test suite to ensure no regressions
- [ ] Verify that `IdempotencyService` still functions correctly
- [ ] Test the new helper function independently
- [ ] Ensure proper error handling in helper function

### Phase 7: Documentation and Cleanup
- [ ] Update test helper documentation
- [ ] Add examples of how to use the new helper
- [ ] Update any related test documentation
- [ ] Clean up any remaining references to old method
- [ ] Commit changes with clear commit message

## Technical Considerations

### Helper Function Signature
```python
# Before (in IdempotencyService)
def simulate_event_processing(
    self,
    event_type: str,
    operation: str,
    user_id: str,
    provider: str,
    event_id: str,
    batch_id: Optional[str] = None,
) -> Dict[str, Any]:

# After (in test helper)
def simulate_event_processing(
    event_type: str,
    operation: str,
    user_id: str,
    provider: str,
    event_id: str,
    batch_id: Optional[str] = None,
    key_generator: Optional[IdempotencyKeyGenerator] = None,
    key_validator: Optional[IdempotencyKeyValidator] = None,
    strategy: Optional[IdempotencyStrategy] = None,
) -> Dict[str, Any]:
```

### Dependencies to Handle
- `IdempotencyKeyGenerator`
- `IdempotencyKeyValidator` 
- `IdempotencyStrategy`
- `datetime` utilities
- Any other dependencies from the original service

### Test Helper Organization Options
1. **Standalone function** in `idempotency_test_helpers.py`
2. **Helper class** with multiple idempotency test utilities
3. **Fixture in conftest.py** if used across many test files
4. **Module-level utilities** for common test patterns

## Benefits
- Cleaner `IdempotencyService` focused on production logic
- Better organized test utilities
- Easier to maintain and update test helpers
- Clearer separation between production and test code
- More reusable test utilities

## Risks
- Need to ensure all dependencies are properly handled
- Tests might break if helper function signature changes
- Need to maintain backward compatibility for existing tests
- Potential import path changes in test files

## Dependencies
- Test infrastructure setup
- Proper import paths for helper utilities
- All required idempotency components available in test environment
- Test runner configuration

## Example Implementation Structure
```python
# services/common/tests/helpers/idempotency_test_helpers.py
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from services.common.idempotency.idempotency_keys import (
    IdempotencyKeyGenerator,
    IdempotencyKeyValidator,
    IdempotencyStrategy,
)

def simulate_event_processing(
    event_type: str,
    operation: str,
    user_id: str,
    provider: str,
    event_id: str,
    batch_id: Optional[str] = None,
    key_generator: Optional[IdempotencyKeyGenerator] = None,
    key_validator: Optional[IdempotencyKeyValidator] = None,
    strategy: Optional[IdempotencyStrategy] = None,
) -> Dict[str, Any]:
    """Simulate event processing to test idempotency configuration."""
    # Implementation moved from IdempotencyService
    pass
```

## Next Steps
1. Review the proposed structure
2. Decide on helper organization approach
3. Begin with Phase 1 analysis
4. Implement changes incrementally
5. Validate all tests pass
6. Clean up production service

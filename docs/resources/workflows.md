# Workflows

Workflows automate document processing in Paperless-ngx. Each workflow has one or more **triggers** (conditions that activate it) and one or more **actions** (what to do when triggered). Triggers and actions are accessible as sub-resources via `paperless.workflows.triggers` and `paperless.workflows.actions`.

## Models

See [`pypaperless/models/workflows/workflow.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/workflows/workflow.py) for all fields and [`pypaperless/models/types.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/types.py) for enum and filter types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Workflows

### Fetch one

```python
workflow = await paperless.workflows(1)
print(workflow.name)  # "Auto-tag invoices"
print(workflow.enabled)  # True
```

### Iterate

```python
async for wf in paperless.workflows:
    print(wf.id, wf.name, "enabled:", wf.enabled)

# Only active workflows
active = [wf async for wf in paperless.workflows if wf.enabled]
```

## Triggers

Triggers are accessed via `paperless.workflows.triggers`:

```python
# Fetch a trigger by id
trigger = await paperless.workflows.triggers(3)
print(trigger.type)  # WorkflowTriggerType.CONSUMPTION
print(trigger.filter_filename)  # "invoice_*.pdf"

# Iterate all triggers
async for trigger in paperless.workflows.triggers:
    print(trigger.id, trigger.type)
```

## Actions

Actions are accessed via `paperless.workflows.actions`:

```python
# Fetch an action by id
action = await paperless.workflows.actions(5)
print(action.type)  # WorkflowActionType.ASSIGNMENT
print(action.assign_tags)  # [1, 3]
print(action.assign_correspondent)  # 7

# Iterate all actions
async for action in paperless.workflows.actions:
    print(action.id, action.type)

# All actions as a dict keyed by id
actions_dict = await paperless.workflows.actions.as_dict()
```

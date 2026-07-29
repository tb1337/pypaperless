"""Workflow snapshot."""

DATA_WORKFLOWS = {
    "count": 3,
    "next": None,
    "previous": None,
    "results": [
        {
            "id": 1,
            "name": "Importordner Template",
            "order": 1,
            "enabled": True,
            "triggers": [
                {
                    "id": 1,
                    "sources": [1],
                    "type": 1,
                    "filter_path": None,
                    "filter_filename": "*.pdf",
                    "filter_mailrule": None,
                    "matching_algorithm": 0,
                    "match": "",
                    "is_insensitive": None,
                    "filter_has_tags": [],
                    "filter_has_correspondent": None,
                    "filter_has_document_type": None,
                }
            ],
            "actions": [
                {
                    "id": 1,
                    "type": 1,
                    "assign_title": "Some workflow title",
                    "assign_tags": [4],
                    "assign_correspondent": 9,
                    "assign_document_type": 8,
                    "assign_storage_path": 2,
                    "assign_owner": 3,
                    "assign_view_users": [],
                    "assign_view_groups": [],
                    "assign_change_users": [],
                    "assign_change_groups": [],
                    "assign_custom_fields": [2],
                }
            ],
        },
        {
            "id": 2,
            "name": "API Upload Template",
            "order": 2,
            "enabled": True,
            "triggers": [
                {
                    "id": 2,
                    "sources": [1, 2],
                    "type": 1,
                    "filter_path": "/api/*",
                    "filter_filename": "*.pdf",
                    "filter_mailrule": None,
                    "matching_algorithm": 0,
                    "match": "",
                    "is_insensitive": None,
                    "filter_has_tags": [],
                    "filter_has_correspondent": None,
                    "filter_has_document_type": None,
                }
            ],
            "actions": [
                {
                    "id": 2,
                    "type": 1,
                    "assign_title": "API",
                    "assign_tags": [4],
                    "assign_correspondent": 9,
                    "assign_document_type": 12,
                    "assign_storage_path": 2,
                    "assign_owner": 3,
                    "assign_view_users": [],
                    "assign_view_groups": [],
                    "assign_change_users": [],
                    "assign_change_groups": [],
                    "assign_custom_fields": [5],
                }
            ],
        },
        {
            "id": 3,
            "name": "Email Template",
            "order": 3,
            "enabled": False,
            "triggers": [
                {
                    "id": 3,
                    "sources": [3],
                    "type": 1,
                    "filter_path": "/mail/*",
                    "filter_filename": "*.eml",
                    "filter_mailrule": 1,
                    "matching_algorithm": 0,
                    "match": "",
                    "is_insensitive": True,
                    "filter_has_tags": [],
                    "filter_has_correspondent": None,
                    "filter_has_document_type": None,
                }
            ],
            "actions": [
                {
                    "id": 3,
                    "type": 1,
                    "assign_title": None,
                    "assign_tags": [],
                    "assign_correspondent": None,
                    "assign_document_type": None,
                    "assign_storage_path": None,
                    "assign_owner": 2,
                    "assign_view_users": [3, 7],
                    "assign_view_groups": [1],
                    "assign_change_users": [6],
                    "assign_change_groups": [],
                    "assign_custom_fields": [],
                }
            ],
        },
    ],
}

_ACTIONS = [action for wf in DATA_WORKFLOWS["results"] for action in wf["actions"]]
_TRIGGERS = [trigger for wf in DATA_WORKFLOWS["results"] for trigger in wf["triggers"]]

DATA_WORKFLOW_ACTIONS = {
    "count": len(_ACTIONS),
    "next": None,
    "previous": None,
    "results": _ACTIONS,
}

DATA_WORKFLOW_TRIGGERS = {
    "count": len(_TRIGGERS),
    "next": None,
    "previous": None,
    "results": _TRIGGERS,
}

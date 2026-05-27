from uuid import uuid4


def generate_trace_id() -> str:
    return str(uuid4())

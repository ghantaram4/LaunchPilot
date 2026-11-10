"""One killable provider request. Secrets travel over stdin, never argv, disk, or logs."""
import json
import sys

from .config import ENDPOINT, MODEL
from .diagnostics import failure_report


def make_model(payload, http_client=None):
    from langchain_openai import ChatOpenAI
    options = {"http_client": http_client} if http_client is not None else {}
    # ChatOpenAI 1.x renames its max_tokens field to max_completion_tokens. Nebius's
    # compatible API uses max_tokens; extra_body preserves that exact wire parameter.
    return ChatOpenAI(api_key=payload["api_key"], base_url=ENDPOINT, model=MODEL,
                      reasoning_effort="low", temperature=1, max_tokens=None,
                      extra_body={"max_tokens": payload["max_tokens"]},
                      timeout=payload["timeout"], max_retries=0, stream_usage=False, **options)


def main():
    from langchain_core.messages import message_to_dict, messages_from_dict
    import openai

    payload = json.load(sys.stdin)
    try:
        model = make_model(payload)
        if payload["tools"]:
            model = model.bind_tools(payload["tools"], tool_choice={"type": "function", "function": {"name": "retrieve_sources"}}, parallel_tool_calls=False)
        elif payload["json_mode"]:
            model = model.bind(response_format={"type": "json_object"})
        response = model.invoke(messages_from_dict(payload["messages"]), config={"callbacks": []})
        # Do not retain hidden reasoning or response headers; keep only user-visible content/tool calls and usage.
        response.additional_kwargs = {}
        response.response_metadata = {}
        print(json.dumps({"ok": True, "message": message_to_dict(response), "usage": response.usage_metadata}))
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        transient = isinstance(exc, (openai.APITimeoutError, openai.APIConnectionError)) or status == 429 or (isinstance(status, int) and status >= 500)
        # Preserve the chain as types/codes only; raw errors, requests and headers can contain secrets/sources.
        print(json.dumps({"ok": False, "kind": f"http_{status}" if status else type(exc).__name__,
                          "transient": transient, "diagnostics": failure_report(exc, credential_loaded=bool(payload.get("api_key")))}))


if __name__ == "__main__":
    main()

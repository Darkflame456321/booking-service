import json
from decimal import Decimal, DecimalException
from urllib.parse import parse_qsl

from rest_framework.exceptions import APIException, ParseError
from rest_framework.parsers import BaseParser

MAX_BODY_BYTES = 1024 * 1024


class BodyTooLarge(APIException):
    status_code = 413
    default_detail = "request body exceeds 1 MiB"


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate field: {key}")
        result[key] = value
    return result


def read_text(stream):
    body = stream.read(MAX_BODY_BYTES + 1)
    if len(body) > MAX_BODY_BYTES:
        raise BodyTooLarge()
    return body.decode("utf-8")


class ExactJSONParser(BaseParser):
    media_type = "application/json"

    def parse(self, stream, media_type=None, parser_context=None):
        try:
            data = json.loads(
                read_text(stream), parse_float=Decimal, object_pairs_hook=unique_pairs
            )
            if not isinstance(data, dict):
                raise ValueError("body must be an object")
            return data
        except (ValueError, UnicodeError, RecursionError, DecimalException) as exc:
            raise ParseError("invalid request body") from exc


class UniqueFormParser(BaseParser):
    media_type = "application/x-www-form-urlencoded"

    def parse(self, stream, media_type=None, parser_context=None):
        try:
            return unique_pairs(
                parse_qsl(
                    read_text(stream), keep_blank_values=True, strict_parsing=True, errors="strict"
                )
            )
        except (ValueError, UnicodeError) as exc:
            raise ParseError("invalid request body") from exc

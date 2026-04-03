# API Errors

All error responses share a common payload and the `X-Request-ID` header.

## Headers

- `X-Request-ID`: unique identifier for the request. You can also send this header in the request to propagate a trace id.

## Payload shape

```json
{
  "detail": "string or list",
  "error": {
    "message": "string",
    "code": "ERROR_CODE",
    "request_id": "string"
  }
}
```

Notes:
- `detail` is kept for backward compatibility. For validation errors, it is a list of Pydantic error objects.
- `error.message` mirrors `detail` when it is a string, otherwise it is a generic message.
- `error.request_id` matches the `X-Request-ID` response header.

## Error codes

- `HTTP_ERROR`: standard HTTP exceptions (404, 403, etc).
- `VALIDATION_ERROR`: request validation errors (422).
- `INTERNAL_SERVER_ERROR`: unexpected server errors (500).
- `CSRF_FORBIDDEN`: CSRF validation failures.

## Account activation (`POST /auth/activate` response body)

The activation endpoint returns a JSON body with `success` and optional `error` string codes (not the standard `error.code` envelope above). Common values:

- `PASSWORD_TOO_SHORT`: new password is shorter than the server’s minimum length (`PASSWORD_MIN_LENGTH`; in production this is at least 12).
- `PASSWORD_REQUIRED`, `CURRENT_PASSWORD_REQUIRED`, `CURRENT_PASSWORD_INVALID`: validation of passwords for the flow.
- `TOKEN_*`, `EMAIL_ALREADY_EXISTS`: token or email state issues.

See backend activation logic for the full set.

## Examples

### CSRF forbidden

```json
{
  "detail": "CSRF token invalido o ausente",
  "error": {
    "message": "CSRF token invalido o ausente",
    "code": "CSRF_FORBIDDEN",
    "request_id": "a1b2c3d4e5f6"
  }
}
```

### Validation error

```json
{
  "detail": [
    {
      "type": "int_parsing",
      "loc": ["body", "count"],
      "msg": "Input should be a valid integer",
      "input": "x"
    }
  ],
  "error": {
    "message": "Request error",
    "code": "VALIDATION_ERROR",
    "request_id": "a1b2c3d4e5f6"
  }
}
```

"""Request validation utilities"""

from functools import wraps
from flask import request, jsonify
from marshmallow import Schema, fields, ValidationError
from typing import Type, Callable, Dict, Any

def validate_request(schema: Type[Schema]) -> Callable:
    """Decorator to validate request data against a schema."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Handle different request content types
                if request.is_json:
                    data = request.get_json()
                elif request.form:
                    data = request.form.to_dict()
                else:
                    data = request.args.to_dict()

                # Validate data against schema
                validated_data = schema().load(data)
                return f(*args, validated_data=validated_data, **kwargs)
            except ValidationError as err:
                return jsonify({"error": "Validation failed", "details": err.messages}), 400
            except Exception as e:
                return jsonify({"error": str(e)}), 400
        return decorated_function
    return decorator

# Schema definitions
class UpdateSchema(Schema):
    """Schema for update validation"""
    message = fields.String(required=True, validate=lambda x: len(x.strip()) > 0)
    process = fields.String(required=True)

class UserSchema(Schema):
    """Schema for user data validation"""
    username = fields.String(required=True)
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=lambda x: len(x) >= 8)

class LoginSchema(Schema):
    """Schema for login validation"""
    username = fields.String(required=True)
    password = fields.String(required=True)

class SOPSummarySchema(Schema):
    """Schema for SOP summary validation"""
    title = fields.String(required=True)
    content = fields.String(required=True)
    category = fields.String(required=True)

class LessonLearnedSchema(Schema):
    """Schema for lesson learned validation"""
    title = fields.String(required=True)
    content = fields.String(required=True)
    category = fields.String(required=True)
    impact = fields.String(required=True)

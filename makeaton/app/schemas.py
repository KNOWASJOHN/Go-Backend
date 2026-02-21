"""
Request validation schemas using Marshmallow
"""

from marshmallow import Schema, fields, validate, ValidationError


class InvoiceRequestSchema(Schema):
    """Schema for invoice generation request"""
    
    chats = fields.List(
        fields.String(required=True),
        required=True,
        validate=validate.Length(min=1, error="At least one chat message is required")
    )
    
    upi_id = fields.String(
        required=True,
        validate=validate.Length(min=3, max=100, error="Invalid UPI ID")
    )
    
    customer_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=200, error="Customer name is required")
    )
    
    customer_phone = fields.String(
        required=False,
        allow_none=True
    )
    
    customer_email = fields.Email(
        required=False,
        allow_none=True
    )
    
    payee_name = fields.String(
        required=False,
        allow_none=True,
        validate=validate.Length(max=100)
    )

# models/order.py
import uuid
from datetime import datetime, timezone
from common.database import db, BaseModel
from models.enums import OrderStatusEnum, PaymentMethodEnum, PaymentStatusEnum, OrderItemStatusEnum # Your enums
from decimal import Decimal

def generate_order_id_string():
    now = datetime.now(timezone.utc)
    return f"ORD-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

class Order(BaseModel):
    __tablename__ = 'orders'

    order_id = db.Column(db.String(50), primary_key=True, default=generate_order_id_string)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    
    order_status = db.Column(db.Enum(OrderStatusEnum), nullable=False, default=OrderStatusEnum.PENDING_PAYMENT, index=True)
    order_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    subtotal_amount = db.Column(db.Numeric(12, 2), nullable=False)
    discount_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'), server_default='0.00')
    tax_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'), server_default='0.00')
    shipping_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'), server_default='0.00')
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="USD")

    payment_method = db.Column(db.Enum(PaymentMethodEnum), nullable=True)
    payment_status = db.Column(db.Enum(PaymentStatusEnum), nullable=False, default=PaymentStatusEnum.PENDING, index=True)
    payment_gateway_transaction_id = db.Column(db.String(255), nullable=True, index=True, unique=True)
    payment_gateway_name = db.Column(db.String(50), nullable=True)

    shipping_address_id = db.Column(db.Integer, db.ForeignKey('user_addresses.address_id', ondelete='SET NULL'), nullable=True)
    billing_address_id = db.Column(db.Integer, db.ForeignKey('user_addresses.address_id', ondelete='SET NULL'), nullable=True)
    
    shipping_method_name = db.Column(db.String(100), nullable=True)
    customer_notes = db.Column(db.Text, nullable=True)
    internal_notes = db.Column(db.Text, nullable=True)


    user = db.relationship('User',back_populates='orders')
    
    items = db.relationship('OrderItem', back_populates='order', cascade='all, delete-orphan', lazy='joined', order_by='OrderItem.order_item_id')
    status_history = db.relationship('OrderStatusHistory', back_populates='order', cascade='all, delete-orphan', lazy='dynamic', order_by='OrderStatusHistory.changed_at.desc()')
    shipments = db.relationship('Shipment', back_populates='order', cascade='all, delete-orphan', lazy='dynamic')
    
    shipping_address_obj = db.relationship('UserAddress', foreign_keys=[shipping_address_id], lazy='joined')
    billing_address_obj = db.relationship('UserAddress', foreign_keys=[billing_address_id], lazy='joined')

    def __repr__(self):
        return f"<Order id={self.order_id} user_id={self.user_id} status='{self.order_status.value}'>"

    def serialize(self, include_items=True, include_history=False, include_shipments=False):
        data = {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "order_status": self.order_status.value,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "subtotal_amount": str(self.subtotal_amount),
            "discount_amount": str(self.discount_amount),
            "tax_amount": str(self.tax_amount),
            "shipping_amount": str(self.shipping_amount),
            "total_amount": str(self.total_amount),
            "currency": self.currency,
            "payment_method": self.payment_method.value if self.payment_method else None,
            "payment_status": self.payment_status.value if self.payment_status else None,
            "payment_gateway_transaction_id": self.payment_gateway_transaction_id,
            "shipping_address_id": self.shipping_address_id,
            "billing_address_id": self.billing_address_id,
            "shipping_method_name": self.shipping_method_name,
            "customer_notes": self.customer_notes,
            "created_at": self.created_at.isoformat() if hasattr(self, 'created_at') and self.created_at else None,
            "updated_at": self.updated_at.isoformat() if hasattr(self, 'updated_at') and self.updated_at else None,
            "shipping_address_details": self.shipping_address_obj.serialize() if self.shipping_address_obj else None,
            "billing_address_details": self.billing_address_obj.serialize() if self.billing_address_obj else None,
        }
        
        if include_items: data["items"] = [item.serialize() for item in (self.items if self.items is not None else [])]
        if include_history: data["status_history"] = [hist.serialize() for hist in self.status_history.all()] 
        if include_shipments: data["shipments"] = [ship.serialize() for ship in self.shipments.all()] 
        return data

class OrderItem(BaseModel): 
    __tablename__ = 'order_items'

    order_item_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.order_id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id', ondelete='SET NULL'), nullable=True)
    merchant_id = db.Column(db.Integer, db.ForeignKey('merchant_profiles.id', ondelete='SET NULL'), nullable=True, index=True)

    product_name_at_purchase = db.Column(db.String(255), nullable=False)
    sku_at_purchase = db.Column(db.String(100), nullable=True) 

    quantity = db.Column(db.Integer, nullable=False)
    unit_price_at_purchase = db.Column(db.Numeric(10, 2), nullable=False) # Price per unit
    item_subtotal_amount = db.Column(db.Numeric(12, 2), nullable=False) 
    final_price_for_item = db.Column(db.Numeric(12, 2), nullable=False) 

    item_status = db.Column(db.Enum(OrderItemStatusEnum), nullable=False, default=OrderItemStatusEnum.PENDING_FULFILLMENT)
    # created_at, updated_at from BaseModel

    order = db.relationship('Order', back_populates='items')
    product = db.relationship('Product', lazy='joined')
    merchant = db.relationship('MerchantProfile', lazy='joined')

    def __repr__(self):
        return f"<OrderItem id={self.order_item_id} order_id={self.order_id} sku='{self.sku_at_purchase}'>"

    def serialize(self):
        return {
            "order_item_id": self.order_item_id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "merchant_id": self.merchant_id,
            "product_name_at_purchase": self.product_name_at_purchase,
            "sku_at_purchase": self.sku_at_purchase,
            "quantity": self.quantity,
            "unit_price_at_purchase": str(self.unit_price_at_purchase),
            "item_subtotal_amount": str(self.item_subtotal_amount),
            "final_price_for_item": str(self.final_price_for_item),
            "item_status": self.item_status.value,
            "created_at": self.created_at.isoformat() if hasattr(self, 'created_at') and self.created_at else None,
            "updated_at": self.updated_at.isoformat() if hasattr(self, 'updated_at') and self.updated_at else None,
        }

class OrderStatusHistory(BaseModel): 
    __tablename__ = 'order_status_history'

    history_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.order_id', ondelete='CASCADE'), nullable=False, index=True)
    status = db.Column(db.Enum(OrderStatusEnum), nullable=False)
    changed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    

    order = db.relationship('Order', back_populates='status_history')
    changed_by_user = db.relationship('User', lazy='joined') 

    def __repr__(self):
        return f"<OrderStatusHistory order_id={self.order_id} status='{self.status.value}'>"

    def serialize(self):
        return {
            "history_id": self.history_id,
            "order_id": self.order_id,
            "status": self.status.value,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "changed_by_user_id": self.changed_by_user_id,
            "user_email": self.changed_by_user.email if self.changed_by_user else None, 
            "notes": self.notes,
        }
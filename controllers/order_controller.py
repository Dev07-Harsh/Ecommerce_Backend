from flask import jsonify, request
from models.order import Order, OrderItem, OrderStatusHistory
from models.enums import OrderStatusEnum, PaymentStatusEnum, PaymentMethodEnum
from models.product_stock import ProductStock
from models.payment_card import PaymentCard
from common.database import db
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import desc

class OrderController:
    @staticmethod
    def create_order(user_id, order_data):
        try:
            # Start a transaction
            db.session.begin_nested()

            # Validate payment card if payment method is card
            payment_card = None
            payment_method = PaymentMethodEnum(order_data.get('payment_method'))
            if payment_method in [PaymentMethodEnum.CREDIT_CARD, PaymentMethodEnum.DEBIT_CARD]:
                if not order_data.get('payment_card_id'):
                    raise ValueError("Payment card ID is required for card payments")
                
                payment_card = PaymentCard.query.filter_by(
                    card_id=order_data['payment_card_id'],
                    user_id=user_id,
                    status='active'
                ).first()
                
                if not payment_card:
                    raise ValueError("Invalid or inactive payment card")
                
                # Update last used timestamp
                payment_card.update_last_used()

            # Check stock availability and update stock quantities
            for item_data in order_data['items']:
                product_id = item_data.get('product_id')
                quantity = item_data.get('quantity')
                
                # Get product stock
                product_stock = ProductStock.query.get(product_id)
                if not product_stock:
                    raise ValueError(f"Product stock not found for product ID: {product_id}")
                
                # Check if sufficient stock is available
                if product_stock.stock_qty < quantity:
                    raise ValueError(f"Insufficient stock for product ID: {product_id}. Available: {product_stock.stock_qty}, Requested: {quantity}")
                
                # Update stock quantity
                product_stock.stock_qty -= quantity

            # Create new order
            new_order = Order(
                user_id=user_id,
                subtotal_amount=Decimal(str(order_data['subtotal_amount'])),
                discount_amount=Decimal(str(order_data.get('discount_amount', '0.00'))),
                tax_amount=Decimal(str(order_data.get('tax_amount', '0.00'))),
                shipping_amount=Decimal(str(order_data.get('shipping_amount', '0.00'))),
                total_amount=Decimal(str(order_data['total_amount'])),
                currency=order_data.get('currency', 'USD'),
                payment_method=payment_method,
                payment_status=PaymentStatusEnum.PENDING,
                order_status=OrderStatusEnum.PENDING_PAYMENT,
                shipping_address_id=order_data.get('shipping_address_id'),
                billing_address_id=order_data.get('billing_address_id'),
                shipping_method_name=order_data.get('shipping_method_name'),
                customer_notes=order_data.get('customer_notes'),
                internal_notes=order_data.get('internal_notes')
            )

            # Create order items
            for item_data in order_data['items']:
                order_item = OrderItem(
                    product_id=item_data.get('product_id'),
                    merchant_id=item_data.get('merchant_id'),
                    product_name_at_purchase=item_data.get('product_name_at_purchase'),
                    sku_at_purchase=item_data.get('sku_at_purchase'),
                    quantity=item_data.get('quantity'),
                    unit_price_at_purchase=Decimal(str(item_data.get('unit_price_at_purchase'))),
                    item_subtotal_amount=Decimal(str(item_data.get('item_subtotal_amount'))),
                    final_price_for_item=Decimal(str(item_data.get('final_price_for_item')))
                )
                new_order.items.append(order_item)

            # Create initial status history
            status_history = OrderStatusHistory(
                status=OrderStatusEnum.PENDING_PAYMENT,
                changed_by_user_id=user_id,
                notes="Order created"
            )
            new_order.status_history.append(status_history)

            db.session.add(new_order)
            db.session.commit()

            # Process payment if payment method is card
            if payment_card:
                try:
                    # Here you would integrate with your payment gateway
                    # For now, we'll simulate a successful payment
                    payment_success = True  # Replace with actual payment gateway integration
                    
                    if payment_success:
                        # Update payment status
                        new_order.payment_status = PaymentStatusEnum.SUCCESSFUL
                        new_order.order_status = OrderStatusEnum.PROCESSING
                        
                        # Add payment success status history
                        payment_history = OrderStatusHistory(
                            order_id=new_order.order_id,
                            status=OrderStatusEnum.PROCESSING,
                            changed_by_user_id=user_id,
                            notes=f"Payment successful via {payment_card.card_brand} ending in {payment_card.last_four_digits}"
                        )
                        db.session.add(payment_history)
                    else:
                        # Handle payment failure
                        new_order.payment_status = PaymentStatusEnum.FAILED
                        new_order.order_status = OrderStatusEnum.PAYMENT_FAILED
                        
                        # Add payment failure status history
                        payment_history = OrderStatusHistory(
                            order_id=new_order.order_id,
                            status=OrderStatusEnum.PAYMENT_FAILED,
                            changed_by_user_id=user_id,
                            notes=f"Payment failed via {payment_card.card_brand} ending in {payment_card.last_four_digits}"
                        )
                        db.session.add(payment_history)
                        
                        # Restore stock quantities
                        for item in new_order.items:
                            if item.product_id:
                                product_stock = ProductStock.query.get(item.product_id)
                                if product_stock:
                                    product_stock.stock_qty += item.quantity
                    
                    db.session.commit()
                    
                except Exception as payment_error:
                    # Handle payment processing error
                    db.session.rollback()
                    raise ValueError(f"Payment processing failed: {str(payment_error)}")

            return new_order.serialize(include_items=True, include_history=True)

        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_order(order_id):
        order = Order.query.get(order_id)
        if not order:
            return None
        return order.serialize(include_items=True, include_history=True, include_shipments=True)

    @staticmethod
    def get_user_orders(user_id, page=1, per_page=10, status=None):
        query = Order.query.filter_by(user_id=user_id)
        
        if status:
            try:
                status_enum = OrderStatusEnum(status)
                query = query.filter_by(order_status=status_enum)
            except ValueError:
                pass
        
        orders = query.order_by(desc(Order.order_date))\
            .paginate(page=page, per_page=per_page)
        
        return {
            'orders': [order.serialize(include_items=True) for order in orders.items],
            'total': orders.total,
            'pages': orders.pages,
            'current_page': orders.page
        }

    @staticmethod
    def update_order_status(order_id, new_status, user_id, notes=None):
        order = Order.query.get(order_id)
        if not order:
            return None

        try:
            # Update order status
            order.order_status = new_status
            
            # Create status history entry
            status_history = OrderStatusHistory(
                order_id=order_id,
                status=new_status,
                changed_by_user_id=user_id,
                notes=notes
            )
            db.session.add(status_history)
            
            db.session.commit()
            return order.serialize(include_items=True, include_history=True)

        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def update_payment_status(order_id, payment_status, transaction_id=None, gateway_name=None):
        try:
            order = Order.query.get(order_id)
            if not order:
                raise ValueError(f"Order not found with ID: {order_id}")

            # Update payment status
            order.payment_status = payment_status
            if transaction_id:
                order.payment_gateway_transaction_id = transaction_id
            if gateway_name:
                order.payment_gateway_name = gateway_name

            # If payment is successful, update order status to processing
            if payment_status == PaymentStatusEnum.SUCCESSFUL:
                order.order_status = OrderStatusEnum.PROCESSING
                status_history = OrderStatusHistory(
                    order_id=order_id,
                    status=OrderStatusEnum.PROCESSING,
                    changed_by_user_id=None,  # System change
                    notes=f"Payment received via {gateway_name or 'payment gateway'}, order moved to processing"
                )
                db.session.add(status_history)
            elif payment_status == PaymentStatusEnum.FAILED:
                order.order_status = OrderStatusEnum.PAYMENT_FAILED
                status_history = OrderStatusHistory(
                    order_id=order_id,
                    status=OrderStatusEnum.PAYMENT_FAILED,
                    changed_by_user_id=None,  # System change
                    notes=f"Payment failed via {gateway_name or 'payment gateway'}"
                )
                db.session.add(status_history)

            db.session.commit()
            return order.serialize(include_items=True, include_history=True)

        except ValueError as ve:
            db.session.rollback()
            raise ve
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to update payment status: {str(e)}")

    @staticmethod
    def cancel_order(order_id, user_id, notes=None):
        order = Order.query.get(order_id)
        if not order:
            return None

        if order.order_status in [OrderStatusEnum.COMPLETED, OrderStatusEnum.CANCELLED]:
            raise ValueError("Cannot cancel an order that is already completed or cancelled")

        try:
            # Update order status
            order.order_status = OrderStatusEnum.CANCELLED
            
            # Create status history entry
            status_history = OrderStatusHistory(
                order_id=order_id,
                status=OrderStatusEnum.CANCELLED,
                changed_by_user_id=user_id,
                notes=notes or "Order cancelled by user"
            )
            db.session.add(status_history)
            
            # Restore stock quantities
            for item in order.items:
                if item.product_id:
                    product_stock = ProductStock.query.get(item.product_id)
                    if product_stock:
                        product_stock.stock_qty += item.quantity
            
            db.session.commit()
            return order.serialize(include_items=True, include_history=True)

        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_all_orders(page=1, per_page=10, status=None, merchant_id=None):
        query = Order.query
        
        if status:
            try:
                status_enum = OrderStatusEnum(status)
                query = query.filter_by(order_status=status_enum)
            except ValueError:
                pass
                
        if merchant_id:
            query = query.join(OrderItem).filter(OrderItem.merchant_id == merchant_id)
        
        orders = query.order_by(desc(Order.order_date))\
            .paginate(page=page, per_page=per_page)
        
        return {
            'orders': [order.serialize(include_items=True) for order in orders.items],
            'total': orders.total,
            'pages': orders.pages,
            'current_page': orders.page
        } 
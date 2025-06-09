from common.database import db
from models.order import Order, OrderItem
from models.enums import OrderStatusEnum, PaymentStatusEnum
from sqlalchemy import and_, or_, distinct
from datetime import datetime, timedelta
from auth.models.models import MerchantProfile, User
import logging

logger = logging.getLogger(__name__)

class MerchantOrderController:
    @staticmethod
    def get_merchant_orders(user_id: int, page: int = 1, per_page: int = 50, status: str = None, 
                          payment_status: str = None, start_date: str = None, end_date: str = None):
        """
        Get all orders for a merchant's products with pagination and filtering
        """
        try:
            # First get the merchant profile from user_id
            merchant = MerchantProfile.query.filter_by(user_id=user_id).first()
            if not merchant:
                raise ValueError(f"No merchant profile found for user ID {user_id}")

            merchant_id = merchant.id
            logger.info(f"Fetching orders for merchant: {merchant.business_name} (ID: {merchant_id})")
            
            # Base query to get orders with merchant's products
            query = Order.query.join(OrderItem).filter(OrderItem.merchant_id == merchant_id).distinct()
            
            
            # Apply order status filter if provided
            if status:
                try:
                    order_status = OrderStatusEnum(status.lower())
                    query = query.filter(Order.order_status == order_status)
                    logger.info(f"Filtering by order status: {status}")
                except ValueError:
                    logger.error(f"Invalid order status: {status}")
                    raise ValueError(f"Invalid order status: {status}")

            # Apply payment status filter if provided
            if payment_status:
                try:
                    payment_status_enum = PaymentStatusEnum(payment_status.lower())
                    query = query.filter(Order.payment_status == payment_status_enum)
                    logger.info(f"Filtering by payment status: {payment_status}")
                except ValueError:
                    logger.error(f"Invalid payment status: {payment_status}")
                    raise ValueError(f"Invalid payment status: {payment_status}")

            # Apply date range filter if provided
            if start_date:
                try:
                    start = datetime.fromisoformat(start_date)
                    query = query.filter(Order.order_date >= start)
                    logger.info(f"Filtering by start date: {start_date}")
                except ValueError:
                    logger.error(f"Invalid start date format: {start_date}")
                    raise ValueError(f"Invalid start date format: {start_date}")

            if end_date:
                try:
                    end = datetime.fromisoformat(end_date)
                    query = query.filter(Order.order_date <= end)
                    logger.info(f"Filtering by end date: {end_date}")
                except ValueError:
                    logger.error(f"Invalid end date format: {end_date}")
                    raise ValueError(f"Invalid end date format: {end_date}")

            # Get total count for pagination
            total = query.count()
            logger.info(f"Total orders found: {total}")

            # Apply pagination
            orders = query.order_by(Order.order_date.desc())\
                         .offset((page - 1) * per_page)\
                         .limit(per_page)\
                         .all()

            logger.info(f"Retrieved {len(orders)} orders for page {page}")

            # Calculate pagination info
            total_pages = (total + per_page - 1) // per_page
            has_next = page < total_pages
            has_prev = page > 1

            # Serialize orders with only the items belonging to this merchant
            serialized_orders = []
            for order in orders:
                order_data = order.serialize(include_items=False, include_history=True)
                # Filter items to only include those from this merchant
                merchant_items = [item.serialize() for item in order.items if item.merchant_id == merchant_id]
                order_data['items'] = merchant_items
                serialized_orders.append(order_data)

            return {
                'orders': serialized_orders,
                'pagination': {
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': total_pages,
                    'has_next': has_next,
                    'has_prev': has_prev
                }
            }

        except Exception as e:
            logger.error(f"Error fetching merchant orders: {str(e)}", exc_info=True)
            db.session.rollback()
            raise e

    @staticmethod
    def get_merchant_order_details(user_id: int, order_id: str):
        """
        Get detailed information about a specific order for a merchant
        """
        try:
            # First get the merchant profile from user_id
            merchant = MerchantProfile.query.filter_by(user_id=user_id).first()
            if not merchant:
                raise ValueError(f"No merchant profile found for user ID {user_id}")

            merchant_id = merchant.id
            logger.info(f"Fetching order details for order_id: {order_id}, merchant: {merchant.business_name}")
            
            # Get order with merchant's items
            order = Order.query.join(OrderItem)\
                             .filter(and_(
                                 Order.order_id == order_id,
                                 OrderItem.merchant_id == merchant_id
                             )).first()

            if not order:
                logger.warning(f"Order {order_id} not found for merchant {merchant.business_name}")
                raise ValueError(f"Order {order_id} not found or not associated with merchant {merchant.business_name}")

            # Get the full order data but filter items to only include merchant's items
            order_data = order.serialize(include_items=False, include_history=True, include_shipments=True)
            merchant_items = [item.serialize() for item in order.items if item.merchant_id == merchant_id]
            logger.info(f"Found {len(merchant_items)} items for merchant {merchant.business_name} in order {order_id}")
            order_data['items'] = merchant_items

            return order_data

        except Exception as e:
            logger.error(f"Error fetching merchant order details: {str(e)}", exc_info=True)
            db.session.rollback()
            raise e

    @staticmethod
    def get_merchant_order_stats(user_id: int, days: int = 30):
        """
        Get order statistics for a merchant
        """
        try:
            # First get the merchant profile from user_id
            merchant = MerchantProfile.query.filter_by(user_id=user_id).first()
            if not merchant:
                raise ValueError(f"No merchant profile found for user ID {user_id}")

            merchant_id = merchant.id
            logger.info(f"Fetching order stats for merchant: {merchant.business_name}, days: {days}")
            
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Get total orders and revenue
            total_orders = Order.query.join(OrderItem)\
                                    .filter(and_(
                                        OrderItem.merchant_id == merchant_id,
                                        Order.order_date >= start_date
                                    )).distinct().count()

            logger.info(f"Total orders in last {days} days: {total_orders}")

            # Get orders by status
            status_counts = db.session.query(
                Order.order_status,
                db.func.count(distinct(Order.order_id))
            ).join(OrderItem)\
             .filter(and_(
                 OrderItem.merchant_id == merchant_id,
                 Order.order_date >= start_date
             ))\
             .group_by(Order.order_status)\
             .all()

            # Get daily order counts
            daily_orders = db.session.query(
                db.func.date(Order.order_date),
                db.func.count(distinct(Order.order_id))
            ).join(OrderItem)\
             .filter(and_(
                 OrderItem.merchant_id == merchant_id,
                 Order.order_date >= start_date
             ))\
             .group_by(db.func.date(Order.order_date))\
             .all()

            stats = {
                'total_orders': total_orders,
                'status_breakdown': {status.value: count for status, count in status_counts},
                'daily_orders': {str(date): count for date, count in daily_orders}
            }
            
            logger.info(f"Order stats for {merchant.business_name}: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error fetching merchant order stats: {str(e)}", exc_info=True)
            db.session.rollback()
            raise e 
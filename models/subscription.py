from datetime import datetime
from common.database import db, BaseModel
from auth.models.models import MerchantProfile, User

class SubscriptionPlan(BaseModel):
    """Subscription plan model for merchant subscriptions."""
    __tablename__ = 'subscription_plans'
    
    plan_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)  # e.g., Basic, Pro, Enterprise
    description = db.Column(db.Text, nullable=True)
    featured_limit = db.Column(db.Integer, nullable=False, default=10)
    promo_limit = db.Column(db.Integer, nullable=False, default=10)
    duration_days = db.Column(db.Integer, nullable=False)  # Plan validity in days
    price = db.Column(db.Numeric(10,2), nullable=False)
    active_flag = db.Column(db.Boolean, default=True, nullable=False)
    can_place_premium = db.Column(db.Boolean, default=False, nullable=False, server_default=db.false())  # Whether this plan allows premium placement
    
    approval_status = db.Column(db.String(20), default='pending', nullable=False)
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    rejection_reason = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    merchant_profiles = db.relationship('MerchantProfile', back_populates='subscription_plan')
    subscription_histories = db.relationship('SubscriptionHistory', back_populates='subscription_plan')
    approved_by_admin = db.relationship('User', backref='approved_plans', foreign_keys=[approved_by])
    
    def serialize(self):
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "description": self.description,
            "featured_limit": self.featured_limit,
            "promo_limit": self.promo_limit,
            "duration_days": self.duration_days,
            "price": float(self.price),
            "active_flag": bool(self.active_flag),
            "can_place_premium": bool(self.can_place_premium),
            "approval_status": self.approval_status,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approved_by": self.approved_by,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None
        }
    
    @classmethod
    def get_by_id(cls, id):
        """Get subscription plan by ID."""
        return cls.query.filter_by(plan_id=id).first()
    
    @classmethod
    def get_by_name(cls, name):
        """Get subscription plan by name."""
        return cls.query.filter_by(name=name).first()

class SubscriptionHistory(BaseModel):
    """Subscription history model to track merchant subscription changes."""
    __tablename__ = 'subscription_histories'
    
    history_id = db.Column(db.Integer, primary_key=True)
    merchant_id = db.Column(db.Integer, db.ForeignKey('merchant_profiles.id'), nullable=False)
    subscription_plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.plan_id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='active', nullable=False)  # active, cancelled, expired
    payment_status = db.Column(db.String(20), default='pending', nullable=False)  # pending, paid, failed
    payment_id = db.Column(db.String(100), nullable=True)
    amount_paid = db.Column(db.Numeric(10,2), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    merchant = db.relationship('MerchantProfile', back_populates='subscription_histories')
    subscription_plan = db.relationship('SubscriptionPlan', back_populates='subscription_histories')
    
    def serialize(self):
        return {
            "history_id": self.history_id,
            "merchant_id": self.merchant_id,
            "subscription_plan_id": self.subscription_plan_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status,
            "payment_status": self.payment_status,
            "payment_id": self.payment_id,
            "amount_paid": float(self.amount_paid) if self.amount_paid else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "subscription_plan": self.subscription_plan.serialize() if self.subscription_plan else None
        }
    
    @classmethod
    def get_by_id(cls, id):
        """Get subscription history by ID."""
        return cls.query.filter_by(history_id=id).first()
    
    @classmethod
    def get_by_merchant_id(cls, merchant_id):
        """Get all subscription histories for a merchant."""
        return cls.query.filter_by(merchant_id=merchant_id).order_by(cls.start_date.desc()).all()
    
    @classmethod
    def get_active_subscription(cls, merchant_id):
        """Get active subscription for a merchant."""
        return cls.query.filter_by(
            merchant_id=merchant_id,
            status='active'
        ).order_by(cls.start_date.desc()).first() 
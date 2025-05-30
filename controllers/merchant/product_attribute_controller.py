from models.product_attribute import ProductAttribute
from models.attribute import Attribute
from models.attribute_value import AttributeValue
from common.database import db
from sqlalchemy.exc import IntegrityError

class MerchantProductAttributeController:
    @staticmethod
    def list(pid):
        """Get all attributes for a product."""
        return ProductAttribute.query.filter_by(product_id=pid).all()

    @staticmethod
    def create(pid, data):
        """
        Create one attribute (single- or multi-value).
        Not used by POST /values (we use upsert there), but still available.
        """
        attribute = Attribute.query.get_or_404(data['attribute_id'])

        # Safely get the raw input_type as a lowercase string
        raw = attribute.input_type
        if hasattr(raw, 'value'):
            itype = raw.value.lower()
        else:
            itype = str(raw).lower()

        vals = []

        # MULTISELECT handling
        if itype == 'multiselect' and isinstance(data.get('value_code'), list):
            for code in data['value_code']:
                AttributeValue.query.get_or_404((attribute.attribute_id, code))
                vals.append(
                    ProductAttribute(
                        product_id=pid,
                        attribute_id=attribute.attribute_id,
                        value_code=code
                    )
                )
        else:
            pa = ProductAttribute(product_id=pid, attribute_id=attribute.attribute_id)

            if itype in ('select', 'multiselect'):
                code = data.get('value_code')
                if code:
                    AttributeValue.query.get_or_404((attribute.attribute_id, code))
                    pa.value_code = code

            elif itype == 'number':
                num = data.get('value_number', data.get('value'))
                try:
                    pa.value_number = float(num)
                except (TypeError, ValueError):
                    raise ValueError(f"Attribute {attribute.attribute_id} expects a number, got {num!r}")

            else:  # text
                txt = data.get('value_text', data.get('value'))
                pa.value_text = str(txt) if txt is not None else None

            vals.append(pa)

        try:
            db.session.add_all(vals)
            db.session.commit()
            return vals if len(vals) > 1 else vals[0]
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Create failed: {e}")

    @staticmethod
    def upsert(pid, attribute_id, value):
        """
        Insert or update a single attribute for a product.
        Now supports:
        - list of codes for multiselect (replaces existing selections)
        - single code for select
        - number for number
        - text for text
        """
        attribute = Attribute.query.get_or_404(attribute_id)

        # Safely get the raw input_type as a lowercase string
        raw = attribute.input_type
        if hasattr(raw, 'value'):
            itype = raw.value.lower()
        else:
            itype = str(raw).lower()

        # Handle MULTISELECT list
        if itype == 'multiselect':
            if not isinstance(value, list):
                raise ValueError("Multiselect attributes require a list of codes")
            # Remove all existing rows for this product/attribute
            ProductAttribute.query.filter_by(
                product_id=pid,
                attribute_id=attribute_id
            ).delete()
            created = []
            for code in value:
                AttributeValue.query.get_or_404((attribute_id, code))
                pa = ProductAttribute(
                    product_id=pid,
                    attribute_id=attribute_id,
                    value_code=code
                )
                db.session.add(pa)
                created.append(pa)
            try:
                db.session.commit()
                return created
            except IntegrityError as e:
                db.session.rollback()
                raise ValueError(f"Upsert multiselect failed: {e}")

        # Otherwise prepare single‐value insert/update
        code = text = num = None

        if itype == 'select':
            if not value:
                raise ValueError("Value required for select")
            AttributeValue.query.get_or_404((attribute_id, value))
            code = value

        elif itype == 'number':
            try:
                num = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"Attribute expects a number, got {value!r}")

        else:  # text
            text = str(value)

        existing = ProductAttribute.query.filter_by(
            product_id=pid,
            attribute_id=attribute_id
        ).first()

        if existing:
            existing.value_code   = code
            existing.value_text   = text
            existing.value_number = num
        else:
            existing = ProductAttribute(
                product_id=pid,
                attribute_id=attribute_id,
                value_code=code,
                value_text=text,
                value_number=num
            )
            db.session.add(existing)

        try:
            db.session.commit()
            return existing
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Upsert failed: {e}")

    @staticmethod
    def update(pid, aid, pa_id, data):
        """
        Update an existing ProductAttribute by its surrogate id.
        """
        pa = ProductAttribute.query.filter_by(
            product_id=pid,
            attribute_id=aid,
            id=pa_id
        ).first_or_404()

        if 'value_code' in data:
            AttributeValue.query.get_or_404((aid, data['value_code']))
            pa.value_code   = data['value_code']
            pa.value_text   = None
            pa.value_number = None

        if 'value_number' in data:
            try:
                pa.value_number = float(data['value_number'])
            except (TypeError, ValueError):
                raise ValueError(f"Invalid number format: {data['value_number']!r}")
            pa.value_code = None
            pa.value_text = None

        if 'value_text' in data:
            pa.value_text   = data['value_text']
            pa.value_code   = None
            pa.value_number = None

        db.session.commit()
        return pa

    @staticmethod
    def delete(pid, aid, pa_id):
        """
        Delete a ProductAttribute row by surrogate id.
        """
        pa = ProductAttribute.query.filter_by(
            product_id=pid,
            attribute_id=aid,
            id=pa_id
        ).first_or_404()
        db.session.delete(pa)
        db.session.commit()
        return True

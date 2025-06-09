from enum import Enum
from typing import List, Dict, Any
from .merchant_document import DocumentType

class CountryCode(Enum):
    """Country codes for supported countries."""
    INDIA = 'IN'
    GLOBAL = 'GLOBAL'  # For all other countries

class CountryConfig:
    """Configuration for country-specific requirements and validations."""
    
    @staticmethod
    def get_required_documents(country_code: str) -> List[DocumentType]:
        """Get list of required documents based on country code."""
        configs = {
            CountryCode.INDIA.value: [
                # Business Registration
                DocumentType.BUSINESS_REGISTRATION_IN,
                # Tax Documents
                DocumentType.PAN_CARD,
                DocumentType.GSTIN,
                # Identity & Address
                DocumentType.AADHAR,
                DocumentType.BUSINESS_ADDRESS_PROOF_IN,
                # Bank Details
                DocumentType.CANCELLED_CHEQUE,
                DocumentType.BANK_ACCOUNT_IN,
                # Tax Compliance
                DocumentType.GST_CERTIFICATE,
                DocumentType.MSME_CERTIFICATE,
                # Digital Signature
                DocumentType.DSC,
                # Required Business Documents
                DocumentType.RETURN_POLICY,
                DocumentType.SHIPPING_DETAILS,
                # Product and Category Documents
                DocumentType.PRODUCT_LIST,
                DocumentType.CATEGORY_LIST,
                DocumentType.BRAND_APPROVAL
            ],
            CountryCode.GLOBAL.value: [
                # Business Registration
                DocumentType.BUSINESS_REGISTRATION_GLOBAL,
                # Tax Documents
                DocumentType.TAX_ID_GLOBAL,
                DocumentType.SALES_TAX_REG,
                # Identity & Address
                DocumentType.PASSPORT,
                DocumentType.BUSINESS_ADDRESS_PROOF_GLOBAL,
                # Bank Details
                DocumentType.BANK_STATEMENT,
                DocumentType.BANK_ACCOUNT_GLOBAL,
                # Tax Compliance
                DocumentType.SALES_TAX_PERMIT,
                DocumentType.SMALL_BUSINESS_CERT,
                # Digital Signature
                DocumentType.ESIGN_CERTIFICATE,
                # Required Business Documents
                DocumentType.RETURN_POLICY,
                DocumentType.SHIPPING_DETAILS,
                # Product and Category Documents
                DocumentType.PRODUCT_LIST,
                DocumentType.CATEGORY_LIST,
                DocumentType.BRAND_APPROVAL
            ]
        }
        return configs.get(country_code, configs[CountryCode.GLOBAL.value])

    @staticmethod
    def get_field_validations(country_code: str) -> Dict[str, Any]:
        """Get field validation rules based on country code."""
        return {
            CountryCode.INDIA.value: {
                'gstin': {
                    'pattern': r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',
                    'message': 'Invalid GSTIN format'
                },
                'pan_number': {
                    'pattern': r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$',
                    'message': 'Invalid PAN number format'
                },
                'bank_ifsc_code': {
                    'pattern': r'^[A-Z]{4}0[A-Z0-9]{6}$',
                    'message': 'Invalid IFSC code format'
                }
            },
            CountryCode.GLOBAL.value: {
                'tax_id': {
                    'pattern': r'^\d{2}-\d{7}$',
                    'message': 'Invalid tax ID format (XX-XXXXXXX)'
                },
                'bank_swift_code': {
                    'pattern': r'^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$',
                    'message': 'Invalid SWIFT/BIC code format'
                }
            }
        }.get(country_code, {})

    @staticmethod
    def get_bank_fields(country_code: str) -> List[str]:
        """Get required bank fields based on country code."""
        return {
            CountryCode.INDIA.value: [
                'bank_account_number',
                'bank_name',
                'bank_branch',
                'bank_ifsc_code'
            ],
            CountryCode.GLOBAL.value: [
                'bank_account_number',
                'bank_name',
                'bank_swift_code',
                'bank_routing_number'
            ]
        }.get(country_code, [
            'bank_account_number',
            'bank_name',
            'bank_swift_code'
        ])

    @staticmethod
    def get_tax_fields(country_code: str) -> List[str]:
        """Get required tax fields based on country code."""
        return {
            CountryCode.INDIA.value: [
                'gstin',
                'pan_number'
            ],
            CountryCode.GLOBAL.value: [
                'tax_id',
                'sales_tax_number'
            ]
        }.get(country_code, ['tax_id'])

    @staticmethod
    def get_country_name(country_code: str) -> str:
        """Get full country name from country code."""
        return {
            CountryCode.INDIA.value: 'India',
            CountryCode.GLOBAL.value: 'International'
        }.get(country_code, 'Unknown')

    @staticmethod
    def get_supported_countries() -> List[Dict[str, str]]:
        """Get list of supported countries with their codes and names."""
        return [
            {'code': country.value, 'name': CountryConfig.get_country_name(country.value)}
            for country in CountryCode
        ]
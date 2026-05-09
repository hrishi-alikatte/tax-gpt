from pydantic import BaseModel, Field
from typing import Optional, List

class UserProfile(BaseModel):
    """Structured representation of the user's tax profile."""
    first_name: Optional[str] = Field(description="The user's first name", default=None)
    marital_status: Optional[str] = Field(description="E.g., Married, Single, Divorced", default=None)
    children_count: Optional[int] = Field(description="Number of children", default=None)
    employment_status: Optional[str] = Field(description="E.g., Employed, Self-employed, Unemployed", default=None)
    has_childcare_expenses: Optional[bool] = Field(description="True if they have daycare/creche costs", default=None)
    
    def get_missing_critical_fields(self) -> List[str]:
        """Completeness Engine: returns a list of fields we should proactively ask about."""
        missing = []
        # If we know they have kids, but don't know about childcare expenses
        if self.children_count is not None and self.children_count > 0:
            if self.has_childcare_expenses is None:
                missing.append("has_childcare_expenses")
                
        # If we don't know employment status, it's critical for taxes
        if self.employment_status is None:
            missing.append("employment_status")
            
        return missing

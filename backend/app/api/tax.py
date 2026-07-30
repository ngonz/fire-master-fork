"""Tax planning API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.engines.monte_carlo import MonteCarloEngine
from app.engines.sepp import compute_sepp
from app.engines.tax_engine import TaxEngine
from app.schemas.tax import (
    ACAAnalysisResponse,
    BracketAnalysisResponse,
    MonteCarloResponse,
    RothConversionPlanResponse,
    SEPPResponse,
    TaxScenarioInput,
    TaxScenarioResponse,
    WithdrawalPlanResponse,
)

router = APIRouter(prefix="/api/tax", tags=["tax"])


@router.get("/bracket-analysis", response_model=BracketAnalysisResponse)
async def get_bracket_analysis(
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Current year income position within brackets, room to next bracket."""
    engine = TaxEngine(db)
    return await engine.analyze_brackets()


@router.get("/withdrawal-plan", response_model=WithdrawalPlanResponse)
async def get_withdrawal_plan(
    years: int = Query(default=10, ge=1, le=50),
    target_bracket: float = Query(
        default=0.22, ge=0.10, le=0.37,
        description="Golden-window Roth conversions fill up to this bracket rate",
    ),
    roth_conversions: bool = Query(
        default=True,
        description="Enable bracket-fill Roth conversions during the golden window",
    ),
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tax-aware year-by-year withdrawal sequence (fixed order + RMDs +
    golden-window bracket-fill Roth conversions)."""
    engine = TaxEngine(db)
    plan = await engine.optimize_withdrawal_sequence(
        years=years,
        target_bracket_rate=target_bracket,
        roth_conversions_enabled=roth_conversions,
    )
    return plan


@router.get("/roth-conversion-plan", response_model=RothConversionPlanResponse)
async def get_roth_conversion_plan(
    target_bracket: float = Query(default=0.22, description="Fill up to this bracket rate"),
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Recommended Roth conversion ladder with tax cost and lifetime savings."""
    engine = TaxEngine(db)
    plan = await engine.plan_roth_conversions(target_bracket_rate=target_bracket)
    return plan


@router.get("/aca-analysis", response_model=ACAAnalysisResponse)
async def get_aca_analysis(
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Current MAGI, ACA subsidy eligibility, cliff warnings."""
    engine = TaxEngine(db)
    analysis = await engine.analyze_brackets()
    aca = analysis["aca"]
    # Get household size from config
    from app.engines.fire_projections import FireProjectionsEngine
    fire_engine = FireProjectionsEngine(db)
    config = await fire_engine.get_or_create_config()
    tax_config = engine._get_tax_config(config)
    return ACAAnalysisResponse(
        magi=aca["magi"],
        household_size=tax_config.get("household_size", 1),
        fpl=aca["magi"] / (aca["fpl_percentage"] / 100) if aca["fpl_percentage"] > 0 else 0,
        fpl_percentage=aca["fpl_percentage"],
        subsidy_eligible=aca["subsidy_eligible"],
        estimated_monthly_premium=aca["monthly_premium"],
        estimated_monthly_subsidy=aca["monthly_subsidy"],
        estimated_net_monthly_cost=aca["net_monthly_cost"],
        cliff_distance=aca["cliff_distance"],
        cliff_warning=aca["cliff_warning"],
    )


@router.post("/scenario", response_model=TaxScenarioResponse)
async def run_tax_scenario(
    data: TaxScenarioInput,
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """What-if: e.g., 'what if I convert $50K to Roth this year?'"""
    engine = TaxEngine(db)
    return await engine.run_tax_scenario(
        roth_conversion=data.roth_conversion,
        extra_income=data.extra_income,
        extra_deduction=data.extra_deduction,
    )


@router.get("/sepp", response_model=SEPPResponse)
async def sepp_calculator(
    balance: float = Query(..., gt=0, description="IRA balance to compute SEPP on (dollars)"),
    age: int = Query(..., ge=21, le=80, description="Owner's age on their birthday in the first distribution year"),
    rate: float = Query(default=0.05, ge=0, description="Interest rate; capped at max(5%, 120% mid-term AFR)"),
    target_monthly: float | None = Query(default=None, gt=0, description="Reverse solve: monthly payment you need — returns the required IRA-A balance"),
    afr_120: float | None = Query(default=None, ge=0, description="120% of the federal mid-term rate, if you want a cap above 5%"),
    _user: str = Depends(get_current_user),
):
    """SEPP / 72(t) calculator — Rev. Rul. 2002-62 as modified by Notice 2022-6.

    Forward: balance + age + rate → annual/monthly payment per IRS method
    (fixed amortization, RMD method). Reverse: target monthly payment →
    required IRA-A balance (the dual-IRA split solver). Pure calculation,
    no data stored.
    """
    try:
        return compute_sepp(
            balance=balance, age=age, rate=rate,
            target_monthly=target_monthly, afr_120_mid_term=afr_120,
        )
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid SEPP calculation parameters.")


@router.get("/monte-carlo", response_model=MonteCarloResponse)
async def run_monte_carlo(
    runs: int = Query(default=1000, ge=100, le=10000),
    seed: int | None = Query(default=None, description="Fix the RNG seed for reproducible runs"),
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Monte Carlo simulation — correlated stochastic returns + inflation, real terms."""
    engine = MonteCarloEngine(db)
    return await engine.run_simulation(n_runs=runs, seed=seed)

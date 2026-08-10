"""Recipe costing API routes — CRUD recipes and ingredients."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.recipe import Recipe, RecipeIngredient

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


class CreateRecipeRequest(BaseModel):
    merchant_id: int
    name: str
    description: str = ""
    selling_price: float = 0
    portions: int = 1


class CreateIngredientRequest(BaseModel):
    merchant_id: int
    square_catalog_object_id: str
    item_name: str
    quantity: float
    unit: str
    cost_per_unit: float = 0.0


@router.post("")
async def create_recipe(body: CreateRecipeRequest, db: Session = Depends(get_db)):
    """Create a new recipe."""
    recipe = Recipe(
        merchant_id=body.merchant_id,
        name=body.name,
        description=body.description,
        selling_price=body.selling_price,
        portions=body.portions,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return {"id": recipe.id, "name": recipe.name}


@router.get("")
async def list_recipes(merchant_id: int, db: Session = Depends(get_db)):
    """List all recipes for the merchant with calculated costs."""
    recipes = db.query(Recipe).filter_by(merchant_id=merchant_id).all()

    result = []
    for r in recipes:
        ingredients = (
            db.query(RecipeIngredient).filter_by(recipe_id=r.id).all()
        )
        total_cost = sum(
            float(ing.quantity) * float(ing.cost_per_unit or 0)
            for ing in ingredients
        )
        cost_per_portion = total_cost / r.portions if r.portions > 0 else total_cost
        margin = float(r.selling_price or 0) - cost_per_portion

        result.append(
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "selling_price": str(r.selling_price),
                "portions": r.portions,
                "ingredient_count": len(ingredients),
                "total_cost": str(round(total_cost, 2)),
                "cost_per_portion": str(round(cost_per_portion, 2)),
                "margin": str(round(margin, 2)),
                "margin_pct": (
                    str(round((margin / float(r.selling_price)) * 100, 1))
                    if float(r.selling_price or 0) > 0
                    else "0"
                ),
            }
        )

    return {"recipes": result, "count": len(result)}


@router.get("/{recipe_id}")
async def get_recipe(recipe_id: int, merchant_id: int, db: Session = Depends(get_db)):
    """Get a single recipe with its ingredients."""
    recipe = (
        db.query(Recipe)
        .filter_by(id=recipe_id, merchant_id=merchant_id)
        .first()
    )
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    ingredients = (
        db.query(RecipeIngredient).filter_by(recipe_id=recipe_id).all()
    )

    total_cost = sum(
        float(ing.quantity) * float(ing.cost_per_unit or 0)
        for ing in ingredients
    )
    cost_per_portion = total_cost / recipe.portions if recipe.portions > 0 else total_cost

    return {
        "id": recipe.id,
        "name": recipe.name,
        "description": recipe.description,
        "selling_price": str(recipe.selling_price),
        "portions": recipe.portions,
        "total_cost": str(round(total_cost, 2)),
        "cost_per_portion": str(round(cost_per_portion, 2)),
        "ingredients": [
            {
                "id": ing.id,
                "square_catalog_object_id": ing.square_catalog_object_id,
                "item_name": ing.item_name,
                "quantity": str(ing.quantity),
                "unit": ing.unit,
                "cost_per_unit": str(ing.cost_per_unit or 0),
                "line_total": str(round(float(ing.quantity) * float(ing.cost_per_unit or 0), 2)),
            }
            for ing in ingredients
        ],
    }


@router.post("/{recipe_id}/ingredients")
async def add_ingredient(
    recipe_id: int,
    body: CreateIngredientRequest,
    db: Session = Depends(get_db),
):
    """Add an ingredient to a recipe."""
    recipe = (
        db.query(Recipe)
        .filter_by(id=recipe_id, merchant_id=body.merchant_id)
        .first()
    )
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    ingredient = RecipeIngredient(
        recipe_id=recipe_id,
        square_catalog_object_id=body.square_catalog_object_id,
        item_name=body.item_name,
        quantity=body.quantity,
        unit=body.unit,
        cost_per_unit=body.cost_per_unit,
    )
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return {"id": ingredient.id, "item_name": ingredient.item_name}


@router.delete("/{recipe_id}/ingredients/{ingredient_id}")
async def remove_ingredient(
    recipe_id: int,
    ingredient_id: int,
    merchant_id: int,
    db: Session = Depends(get_db),
):
    """Remove an ingredient from a recipe."""
    recipe = (
        db.query(Recipe)
        .filter_by(id=recipe_id, merchant_id=merchant_id)
        .first()
    )
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    ingredient = (
        db.query(RecipeIngredient)
        .filter_by(id=ingredient_id, recipe_id=recipe_id)
        .first()
    )
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    db.delete(ingredient)
    db.commit()
    return {"status": "deleted"}

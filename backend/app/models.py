from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Ingredient(StrictModel):
    id: str
    name: str
    unit: Literal['g', 'ml', 'un.']
    pack: float = Field(gt=0)
    price: float = Field(ge=0)

class Recipe(StrictModel):
    id: str
    name: str
    description: str
    category: str
    minutes: int = Field(gt=0)
    tag: str
    image: str
    needs: dict[str, float]

    @model_validator(mode='after')
    def quantities_positive(self):
        if not self.needs or any(q <= 0 for q in self.needs.values()):
            raise ValueError('Receita deve conter quantidades positivas.')
        return self

class Product(StrictModel):
    ingredient_id: str
    pack: float = Field(gt=0)
    unit: Literal['g', 'ml', 'un.']
    price_cents: int = Field(ge=0)
    stock: int = Field(ge=0)

class Store(StrictModel):
    id: str
    name: str
    initials: str
    color: str
    freight: float = Field(ge=0)
    minimum: float = Field(ge=0)
    minutes: int = Field(gt=0)
    products: list[Product]

class Catalog(StrictModel):
    schema_version: Literal[1]
    simulated: Literal[True]
    currency: Literal['BRL']
    ingredients: list[Ingredient]
    recipes: list[Recipe]
    stores: list[Store]

    @model_validator(mode='after')
    def references(self):
        for items in (self.ingredients, self.recipes, self.stores):
            ids = [i.id for i in items]
            if len(ids) != len(set(ids)):
                raise ValueError('IDs duplicados no catálogo.')
        units = {i.id: i.unit for i in self.ingredients}
        for recipe in self.recipes:
            if not set(recipe.needs) <= units.keys():
                raise ValueError('Ingrediente desconhecido na receita.')
        for store in self.stores:
            ids = [p.ingredient_id for p in store.products]
            if len(ids) != len(set(ids)):
                raise ValueError('Produto duplicado no mercado.')
            for p in store.products:
                if units.get(p.ingredient_id) != p.unit:
                    raise ValueError('Produto com ingrediente ou unidade incompatível.')
        if len(self.ingredients) > 16:
            raise ValueError('Catálogo excede limite de 16 ingredientes do otimizador exato.')
        return self

class PlanRequest(StrictModel):
    recipe_ids: list[str] = Field(max_length=10)
    servings: int = Field(default=2, ge=1, le=12, strict=True)
    pantry_ids: list[str] = Field(default_factory=list, max_length=16)
    split: bool = False
    sort: Literal['price', 'time'] = 'price'

    @model_validator(mode='after')
    def unique_ids(self):
        if len(set(self.recipe_ids)) != len(self.recipe_ids) or len(set(self.pantry_ids)) != len(self.pantry_ids):
            raise ValueError('IDs repetidos na solicitação.')
        return self

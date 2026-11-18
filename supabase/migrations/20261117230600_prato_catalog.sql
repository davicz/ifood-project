-- Prato: catálogo simulado em BRL. Execute o arquivo inteiro no SQL Editor.
-- Estoque = número de embalagens. Quantidade das receitas = por pessoa.
-- O schema prato fica fora do schema public usado pela Data API por padrão.
begin;

create schema if not exists prato;
revoke all on schema prato from public, anon, authenticated;

create table if not exists prato.ingredients (
    id text primary key,
    name text not null,
    unit text not null check (unit in ('g', 'ml', 'un.')),
    reference_pack numeric not null check (reference_pack > 0),
    reference_price_cents integer not null check (reference_price_cents >= 0),
    unique (id, unit)
);

create table if not exists prato.recipes (
    id text primary key,
    name text not null,
    description text not null,
    category text not null,
    minutes integer not null check (minutes > 0),
    tag text not null,
    image text not null
);

create table if not exists prato.recipe_ingredients (
    recipe_id text not null references prato.recipes (id),
    ingredient_id text not null references prato.ingredients (id),
    quantity_per_serving numeric not null check (quantity_per_serving > 0),
    primary key (recipe_id, ingredient_id)
);

create table if not exists prato.stores (
    id text primary key,
    name text not null,
    initials text not null,
    color text not null,
    freight_cents integer not null check (freight_cents >= 0),
    minimum_cents integer not null check (minimum_cents >= 0),
    minutes integer not null check (minutes > 0)
);

create table if not exists prato.store_products (
    store_id text not null references prato.stores (id),
    ingredient_id text not null,
    unit text not null,
    pack numeric not null check (pack > 0),
    price_cents integer not null check (price_cents >= 0),
    stock integer not null check (stock >= 0),
    primary key (store_id, ingredient_id),
    foreign key (ingredient_id, unit) references prato.ingredients (id, unit)
);

alter table prato.ingredients enable row level security;
alter table prato.recipes enable row level security;
alter table prato.recipe_ingredients enable row level security;
alter table prato.stores enable row level security;
alter table prato.store_products enable row level security;

revoke all on all tables in schema prato from public, anon, authenticated;

-- Carga inicial: repetir o SQL preserva preços, estoques e demais dados já cadastrados.

insert into prato.ingredients (id, name, unit, reference_pack, reference_price_cents)
values
    ('chicken', 'Peito de frango', 'g', 500, 1590),
    ('rice', 'Arroz branco', 'g', 1000, 690),
    ('cream', 'Creme de leite', 'g', 200, 420),
    ('tomato', 'Tomate', 'g', 500, 550),
    ('pasta', 'Macarrão', 'g', 500, 640),
    ('beef', 'Carne moída', 'g', 500, 2290),
    ('lettuce', 'Alface', 'un.', 1, 450),
    ('chickpea', 'Grão-de-bico cozido', 'g', 300, 890),
    ('bread', 'Pão de hambúrguer', 'un.', 4, 990),
    ('cheese', 'Queijo muçarela', 'g', 200, 1050)
on conflict (id) do nothing;

insert into prato.recipes (id, name, description, category, minutes, tag, image)
values
    ('strogonoff', 'Estrogonofe de frango', 'O clássico que sempre dá vontade de repetir.', 'Dia a dia', 30, 'Favorito da semana', 'photo-1547592180-85f173990554'),
    ('pasta', 'Macarrão à bolonhesa', 'Molho caseiro e um almoço sem complicação.', 'Massas', 35, 'Para compartilhar', 'photo-1551892374-ecf8754cf8b0'),
    ('salad', 'Salada de grão-de-bico', 'Colorida, fresquinha e cheia de sabor.', 'Vegetarianos', 15, 'Leve & prática', 'photo-1512621776951-a57141f2eefd'),
    ('burger', 'Hambúrguer caseiro', 'Seu fim de semana merece esse capricho.', 'Dia a dia', 25, 'Noite especial', 'photo-1568901346375-23c9450c58cd'),
    ('bowl', 'Bowl de frango e salada', 'Tudo que você precisa em um prato só.', 'Até 30 min', 25, 'Almoço resolvido', 'photo-1511690743698-d9d85f2fbf38'),
    ('vegpasta', 'Pasta com tomate e queijo', 'Poucos ingredientes. Muito conforto.', 'Vegetarianos', 20, 'Poucos ingredientes', 'photo-1473093295043-cdd812d0e601')
on conflict (id) do nothing;

insert into prato.recipe_ingredients (recipe_id, ingredient_id, quantity_per_serving)
values
    ('strogonoff', 'chicken', 150),
    ('strogonoff', 'rice', 80),
    ('strogonoff', 'cream', 70),
    ('strogonoff', 'tomato', 60),
    ('pasta', 'pasta', 100),
    ('pasta', 'beef', 100),
    ('pasta', 'tomato', 120),
    ('pasta', 'cheese', 30),
    ('salad', 'chickpea', 120),
    ('salad', 'lettuce', 0.25),
    ('salad', 'tomato', 100),
    ('burger', 'beef', 150),
    ('burger', 'bread', 1),
    ('burger', 'cheese', 40),
    ('burger', 'lettuce', 0.15),
    ('burger', 'tomato', 50),
    ('bowl', 'chicken', 150),
    ('bowl', 'rice', 60),
    ('bowl', 'lettuce', 0.25),
    ('bowl', 'tomato', 100),
    ('vegpasta', 'pasta', 100),
    ('vegpasta', 'tomato', 150),
    ('vegpasta', 'cheese', 60),
    ('vegpasta', 'cream', 40)
on conflict (recipe_id, ingredient_id) do nothing;

insert into prato.stores (id, name, initials, color, freight_cents, minimum_cents, minutes)
values
    ('a', 'Mercado da Vila', 'mv', '#236b49', 590, 2000, 45),
    ('b', 'Bom Preço', 'bp', '#e99b19', 890, 2000, 35),
    ('c', 'Super Express', 'se', '#6851a3', 490, 1500, 20)
on conflict (id) do nothing;

insert into prato.store_products (store_id, ingredient_id, unit, pack, price_cents, stock)
values
    ('a', 'chicken', 'g', 500, 1590, 100),
    ('a', 'rice', 'g', 1000, 690, 100),
    ('a', 'cream', 'g', 200, 420, 100),
    ('a', 'tomato', 'g', 500, 550, 100),
    ('a', 'pasta', 'g', 500, 640, 100),
    ('a', 'beef', 'g', 500, 2290, 100),
    ('a', 'lettuce', 'un.', 1, 450, 100),
    ('a', 'chickpea', 'g', 300, 890, 100),
    ('a', 'bread', 'un.', 4, 990, 100),
    ('a', 'cheese', 'g', 200, 1050, 100),
    ('b', 'chicken', 'g', 500, 1383, 0),
    ('b', 'rice', 'g', 1000, 600, 100),
    ('b', 'cream', 'g', 200, 365, 100),
    ('b', 'tomato', 'g', 500, 479, 100),
    ('b', 'pasta', 'g', 500, 557, 0),
    ('b', 'beef', 'g', 500, 1992, 100),
    ('b', 'lettuce', 'un.', 1, 392, 100),
    ('b', 'chickpea', 'g', 300, 774, 100),
    ('b', 'bread', 'un.', 4, 861, 100),
    ('b', 'cheese', 'g', 200, 914, 100),
    ('c', 'chicken', 'g', 500, 1844, 100),
    ('c', 'rice', 'g', 1000, 800, 100),
    ('c', 'cream', 'g', 200, 487, 100),
    ('c', 'tomato', 'g', 500, 638, 100),
    ('c', 'pasta', 'g', 500, 742, 100),
    ('c', 'beef', 'g', 500, 2656, 100),
    ('c', 'lettuce', 'un.', 1, 522, 100),
    ('c', 'chickpea', 'g', 300, 1032, 100),
    ('c', 'bread', 'un.', 4, 1148, 100),
    ('c', 'cheese', 'g', 200, 1218, 100)
on conflict (store_id, ingredient_id) do nothing;

commit;

select
    (select count(*) from prato.ingredients) as ingredientes,
    (select count(*) from prato.recipes) as receitas,
    (select count(*) from prato.recipe_ingredients) as itens_de_receita,
    (select count(*) from prato.stores) as mercados,
    (select count(*) from prato.store_products) as ofertas;

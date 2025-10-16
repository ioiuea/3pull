"""
アイテムエンドポイント

このモジュールはアイテムのCRUD操作を提供します。
"""

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import ItemCreate, ItemResponse

router = APIRouter()

items_db: dict[int, ItemResponse] = {}
next_id = 1


@router.get("/items", response_model=list[ItemResponse], tags=["items"])
async def get_items() -> list[ItemResponse]:
    """
    全アイテムを取得

    データベースから全てのアイテムを取得します。

    Returns:
        list[ItemResponse]: アイテムリスト

    Examples:
        >>> items = await get_items()
        >>> len(items)
        0
    """
    return list(items_db.values())


@router.get("/items/{item_id}", response_model=ItemResponse, tags=["items"])
async def get_item(item_id: int) -> ItemResponse:
    """
    アイテムを取得

    指定されたIDのアイテムを取得します。

    Args:
        item_id: アイテムID

    Returns:
        ItemResponse: アイテム情報

    Raises:
        HTTPException: アイテムが見つからない場合（404）

    Examples:
        >>> item = await get_item(1)
        >>> item.id
        1
    """
    if item_id not in items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"アイテムID {item_id} は見つかりませんでした",
        )
    return items_db[item_id]


@router.post(
    "/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["items"],
)
async def create_item(item: ItemCreate) -> ItemResponse:
    """
    アイテムを作成

    新しいアイテムをデータベースに作成します。

    Args:
        item: 作成するアイテムの情報

    Returns:
        ItemResponse: 作成されたアイテム情報

    Examples:
        >>> new_item = ItemCreate(name="テスト", price=100.0)
        >>> created = await create_item(new_item)
        >>> created.name
        'テスト'
    """
    global next_id
    new_item = ItemResponse(id=next_id, **item.model_dump())
    items_db[next_id] = new_item
    next_id += 1
    return new_item

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Collection, Document, User
from ..schemas import CollectionCreate, CollectionOut

router = APIRouter(prefix="/api/collections", tags=["collections"])


def _to_out(db: Session, c: Collection) -> CollectionOut:
    count = db.scalar(
        select(func.count(Document.id)).where(Document.collection_id == c.id)
    )
    return CollectionOut(
        id=c.id,
        name=c.name,
        description=c.description,
        document_count=int(count or 0),
        created_at=c.created_at,
    )


def get_owned_collection(collection_id: str, db: Session, user: User) -> Collection:
    c = db.get(Collection, collection_id)
    if c is None or c.user_id != user.id:
        raise HTTPException(status_code=404, detail="Collection not found")
    return c


@router.get("", response_model=list[CollectionOut])
def list_collections(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(
        select(Collection).where(Collection.user_id == user.id).order_by(Collection.created_at.desc())
    ).all()
    return [_to_out(db, c) for c in rows]


@router.post("", response_model=CollectionOut, status_code=201)
def create_collection(
    body: CollectionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = Collection(user_id=user.id, name=body.name, description=body.description)
    db.add(c)
    db.commit()
    db.refresh(c)
    return _to_out(db, c)


@router.get("/{collection_id}", response_model=CollectionOut)
def get_collection(
    collection_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = get_owned_collection(collection_id, db, user)
    return _to_out(db, c)


@router.delete("/{collection_id}", status_code=204)
def delete_collection(
    collection_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = get_owned_collection(collection_id, db, user)
    db.delete(c)
    db.commit()

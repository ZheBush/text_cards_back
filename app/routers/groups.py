from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.card_list import CardList
from app.models.user import User, UserRole
from app.models.group import Group, user_group
from app.schemas.group import GroupCreate, GroupResponse, AddUserToGroup
from app.core.utils import generate_uuid

router = APIRouter()


@router.post("/", response_model=GroupResponse)
async def create_group(
        group_data: GroupCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    if current_user.role != UserRole.manager:
        raise HTTPException(status_code=403, detail="Only managers can create groups")

    new_group = Group(
        id=generate_uuid(),
        name=group_data.name,
        created_by=current_user.id
    )
    db.add(new_group)
    await db.flush()

    stmt = user_group.insert().values(
        user_id=current_user.id,
        group_id=new_group.id,
        role_in_group='manager'
    )
    await db.execute(stmt)
    await db.commit()
    await db.refresh(new_group)
    return new_group


@router.get("/my", response_model=list[GroupResponse])
async def get_my_groups(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    if current_user.role == UserRole.manager:
        result = await db.execute(
            select(Group).where(
                (Group.created_by == current_user.id) |
                (Group.id.in_(
                    select(user_group.c.group_id).where(
                        user_group.c.user_id == current_user.id,
                        user_group.c.role_in_group == 'manager'
                    )
                ))
            )
        )
    else:
        result = await db.execute(
            select(Group).where(
                Group.id.in_(
                    select(user_group.c.group_id).where(
                        user_group.c.user_id == current_user.id
                    )
                )
            )
        )
    groups = result.scalars().all()

    return groups


@router.get("/{group_id}/card_lists")
async def get_group_card_lists(
        group_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    stmt = select(user_group).where(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id
    )

    result = await db.execute(stmt)

    if not result.first():
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this group"
        )

    stmt = select(CardList).where(CardList.group_id == group_id, CardList.user_id == current_user.id)
    result = await db.execute(stmt)

    card_lists = result.scalars().all()

    return card_lists


@router.post("/{group_id}/add_user")
async def add_user_to_group(
        group_id: str,
        data: AddUserToGroup,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    if current_user.role != UserRole.manager:
        raise HTTPException(status_code=403, detail="Only managers can add users to groups")

    group = await db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    stmt = select(user_group).where(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id,
        user_group.c.role_in_group == 'manager'
    )
    result = await db.execute(stmt)
    if not result.first() and group.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="You are not a manager of this group")

    user = await db.get(User, data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = select(user_group).where(
        user_group.c.user_id == data.user_id,
        user_group.c.group_id == group_id
    )
    existing = await db.execute(stmt)
    if existing.first():
        raise HTTPException(status_code=400, detail="User already in group")

    stmt = user_group.insert().values(
        user_id=data.user_id,
        group_id=group_id,
        role_in_group=data.role_in_group
    )
    await db.execute(stmt)
    await db.commit()
    await db.refresh(group)
    return {"message": "User added to group"}


@router.delete("/{group_id}/remove_user/{user_id}")
async def remove_user_from_group(
        group_id: str,
        user_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    if current_user.role != UserRole.manager:
        raise HTTPException(status_code=403, detail="Only managers can remove users from groups")

    group = await db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    stmt = select(user_group).where(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id,
        user_group.c.role_in_group == 'manager'
    )
    result = await db.execute(stmt)
    if not result.first() and group.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="You are not a manager of this group")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = select(user_group).where(
        user_group.c.user_id == user_id,
        user_group.c.group_id == group_id
    )
    existing = await db.execute(stmt)
    if not existing.first():
        raise HTTPException(status_code=400, detail="User is not in this group")

    stmt = user_group.delete().where(
        user_group.c.user_id == user_id,
        user_group.c.group_id == group_id
    )
    await db.execute(stmt)
    await db.commit()

    return {"message": "User removed from group"}


@router.get("/{group_id}/users")
async def get_group_users(
        group_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    stmt = select(user_group).where(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id
    )
    result = await db.execute(stmt)
    if not result.first():
        raise HTTPException(status_code=403, detail="You are not a member of this group")

    stmt = select(User.id, User.email, user_group.c.role_in_group).where(
        user_group.c.group_id == group_id,
        user_group.c.user_id == User.id
    )
    result = await db.execute(stmt)
    users = result.all()
    return [{"id": u.id, "email": u.email, "role_in_group": u.role_in_group} for u in users]
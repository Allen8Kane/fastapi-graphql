from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import Field
from pydantic.dataclasses import dataclass
import strawberry
from strawberry.fastapi import GraphQLRouter
from pony.orm import Database, PrimaryKey, Required, db_session

app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


db = Database(provider='sqlite', filename='database.db', create_db=True)

class UserModel(db.Entity):
    _table_ = "Users"
    id = PrimaryKey(int, auto=True)
    first_name = Required(str)
    salary = Required(int)

db.generate_mapping(create_tables=True)

@dataclass
class UserDTO:
    first_name: str
    salary: int = Field(ge=0)

@strawberry.type(name="User")
class UserType:
    id: int
    first_name: str
    salary: int

@strawberry.input
class UserInput:
    first_name: str
    salary: int

@strawberry.type
class Query:

    @strawberry.field
    def getUsers(self) -> List[UserType]: # TODO: nullable type User
        with db_session:
            users = UserModel.select()
            result = [UserType(**u.to_dict()) for u in users]
        return result
    
    @strawberry.field
    def getUser(self, id: int) -> UserType:
        with db_session:
            if UserModel.exists(id=id):
                user = UserModel[id]
                result = UserType(**user.to_dict())
            else:
                raise HTTPException(status_code=404)
        return result
    

@strawberry.type
class Mutation:

    @strawberry.mutation
    def create_user(self, userInput: UserInput) -> UserType:
        UserDTO(**userInput.__dict__)
        with db_session:
            user = UserModel(**userInput.__dict__)
            db.commit()
            result = UserType(**user.to_dict())
        return result

    @strawberry.mutation
    def update_user(self, id: int, userInput: UserInput) -> UserType:
        UserDTO(**userInput.__dict__)
        with db_session:
            user = UserModel[id]
            user.first_name = userInput.first_name
            user.salary = userInput.salary
            db.commit()
            result = UserType(**user.to_dict())
        return result

    @strawberry.mutation
    def delete_user(self, id: int) -> UserType:
        with db_session:
            db.commit()
            if UserModel.exists(id=id):
                user = UserModel[id]
                result = UserType(**user.to_dict())
                user.delete()
            else:
                raise HTTPException(status_code=404, detail=f"User with id of {id} not found")
            db.commit()
        return result

schema = strawberry.Schema(query=Query, mutation=Mutation)

graphql_app = GraphQLRouter(schema)

app.include_router(graphql_app, prefix="/graphql")
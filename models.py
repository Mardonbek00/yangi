from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)  # telegram user id
    full_name = Column(String(255))
    phone = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class Direction(Base):
    __tablename__ = "directions"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    active = Column(Boolean, default=True)


class Driver(Base):
    __tablename__ = "drivers"

    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    full_name = Column(String(255))
    phone = Column(String(50))
    car_plate = Column(String(50))
    car_model = Column(String(100))
    car_color = Column(String(50))
    status = Column(String(20), default="pending")  # pending / approved / rejected

    balance = Column(Integer, default=0)
    is_online = Column(Boolean, default=False)
    direction_id = Column(Integer, ForeignKey("directions.id"), nullable=True)
    queue_joined_at = Column(DateTime, nullable=True)
    seats_taken = Column(Integer, default=0)

    rating_sum = Column(Integer, default=0)
    rating_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    direction = relationship("Direction")

    @property
    def avg_rating(self):
        if not self.rating_count:
            return None
        return round(self.rating_sum / self.rating_count, 1)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    passenger_id = Column(BigInteger, ForeignKey("users.id"))
    direction_id = Column(Integer, ForeignKey("directions.id"))
    phone = Column(String(50))
    comment = Column(Text, nullable=True)

    # waiting -> offered -> accepted -> completed
    #                                 -> cancelled
    status = Column(String(20), default="waiting")
    driver_id = Column(BigInteger, ForeignKey("drivers.user_id"), nullable=True)
    offer_expires_at = Column(DateTime, nullable=True)
    rating = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    direction = relationship("Direction")
    driver = relationship("Driver")


class OrderRejection(Base):
    """Bitta buyurtmani rad etgan/ulgurmagan haydovchilarni eslab qolish uchun."""
    __tablename__ = "order_rejections"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    driver_id = Column(BigInteger, ForeignKey("drivers.user_id"))

    __table_args__ = (UniqueConstraint("order_id", "driver_id", name="uq_order_driver"),)


class Topup(Base):
    __tablename__ = "topups"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    amount = Column(Integer)
    screenshot_file_id = Column(String(255))
    status = Column(String(20), default="pending")  # pending / approved / rejected
    created_at = Column(DateTime, default=datetime.utcnow)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(50), primary_key=True)
    value = Column(String(255))

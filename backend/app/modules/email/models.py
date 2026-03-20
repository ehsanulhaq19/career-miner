from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.database import Base


class EmailLog(Base):
    """
    SQLAlchemy model representing an email send log entry.
    """

    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    file_attachment = Column(String(1000), nullable=True)
    to_email = Column(String(255), nullable=False)
    from_email = Column(String(255), nullable=True)
    response = Column(Text, nullable=True)
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

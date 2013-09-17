""" owen.db.models - SQLAlchemy models for ticket info. """
from datetime import datetime

import sqlalchemy
import sqlalchemy.sql

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Machine(Base):
    __tablename__ = 'machines'
    
    id = Column(Integer, primary_key=True)
    hostname = Column(String)
    machine_type = Column(String)
    serial = Column(String)
    
    def __repr__(self):
        return "<Machine('%s','%s','%s')>" % (
            self.hostname, self.machine_type, self.serial)

class Part(Base):
    __tablename__ = 'parts'
    
    id = Column(Integer, primary_key=True)
    fru = Column(String)
    description = Column(String) 

    def __repr__(self):
        return "<Part('%s','%s')>" % (self.description, self.fru)
    


class PartRequest(Base):
    __tablename__ = 'part_requests'

    id = Column(Integer, primary_key=True)
    closed = Column(Boolean, default=False)
    machine_id = Column(Integer, ForeignKey('machines.id'))
    machine = relationship("Machine",
        backref=backref('part_requests', order_by=id))
    part_id = Column(Integer, ForeignKey('parts.id'))
    part = relationship("Part",
        backref=backref('requested', order_by=id))
    part_count = Column(Integer)
    ticket_number = Column(String)
    status = Column(String)
    date_created = Column(DateTime,
        default=datetime.now(),
        server_default=sqlalchemy.sql.func.current_timestamp())
    date_closed  = Column(DateTime)
    
    def close(self):
        self.closed = True
        self.date_closed = datetime.now()

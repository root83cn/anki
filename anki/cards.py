# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import time
from anki.utils import intTime, hexifyID, timestampID

# Cards
##########################################################################

# Type: 0=new, 1=learning, 2=due
# Queue: same as above, and:
#        -1=suspended, -2=user buried, -3=sched buried
# Due is used differently for different queues.
# - new queue: fact id or random int
# - rev queue: integer day
# - lrn queue: integer timestamp

class Card(object):

    def __init__(self, deck, id=None):
        self.deck = deck
        self.timerStarted = None
        self._qa = None
        self._rd = None
        if id:
            self.id = id
            self.load()
        else:
            # to flush, set fid, ord, and due
            self.id = timestampID(deck.db, "cards")
            self.gid = 1
            self.crt = intTime()
            self.type = 0
            self.queue = 0
            self.ivl = 0
            self.factor = 0
            self.reps = 0
            self.lapses = 0
            self.left = 0
            self.edue = 0
            self.flags = 0
            self.data = ""

    def load(self):
        (self.id,
         self.fid,
         self.gid,
         self.ord,
         self.mod,
         self.usn,
         self.type,
         self.queue,
         self.due,
         self.ivl,
         self.factor,
         self.reps,
         self.lapses,
         self.left,
         self.edue,
         self.flags,
         self.data) = self.deck.db.first(
             "select * from cards where id = ?", self.id)
        self._qa = None
        self._rd = None

    def flush(self):
        self.mod = intTime()
        self.usn = self.deck.usn()
        self.deck.db.execute(
            """
insert or replace into cards values
(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            self.id,
            self.fid,
            self.gid,
            self.ord,
            self.mod,
            self.usn,
            self.type,
            self.queue,
            self.due,
            self.ivl,
            self.factor,
            self.reps,
            self.lapses,
            self.left,
            self.edue,
            self.flags,
            self.data)

    def flushSched(self):
        self.mod = intTime()
        self.usn = self.deck.usn()
        self.deck.db.execute(
            """update cards set
mod=?, usn=?, type=?, queue=?, due=?, ivl=?, factor=?, reps=?,
lapses=?, left=?, edue=? where id = ?""",
            self.mod, self.usn, self.type, self.queue, self.due, self.ivl,
            self.factor, self.reps, self.lapses,
            self.left, self.edue, self.id)

    def q(self, reload=False):
        return self._getQA(reload)['q']

    def a(self):
        return self._getQA()['a']

    def _getQA(self, reload=False):
        if not self._qa or reload:
            f = self.fact(); m = self.model()
            data = [self.id, f.id, m['id'], self.gid, self.ord, f.stringTags(),
                    f.joinedFields()]
            self._qa = self.deck._renderQA(data)
        return self._qa

    def _reviewData(self, reload=False):
        "Fetch the model and fact."
        if not self._rd or reload:
            f = self.deck.getFact(self.fid)
            m = self.deck.models.get(f.mid)
            self._rd = [f, m]
        return self._rd

    def fact(self):
        return self._reviewData()[0]

    def model(self, reload=False):
        return self._reviewData()[1]

    def groupConf(self):
        return self.deck.groups.conf(self.gid)

    def template(self):
        return self._reviewData()[1]['tmpls'][self.ord]

    def startTimer(self):
        self.timerStarted = time.time()

    def timeTaken(self):
        "Time taken to answer card, in integer MS."
        total = int((time.time() - self.timerStarted)*1000)
        return min(total, self.groupConf()['maxTaken']*1000)

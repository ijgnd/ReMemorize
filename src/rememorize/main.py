# -*- coding: utf-8 -*-
# Copyright: (C) 2018-2019 Lovac42
# Support: https://github.com/lovac42/ReMemorize
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
# Version: 0.2.6


import aqt, random
from aqt import mw
from anki.hooks import wrap
from aqt.utils import getText
from anki.utils import ids2str
from .rememorize import *
from .utils import *
from .const import *
import anki.sched


remem=ReMemorize()


#Reset sibling cards on forget
def answerCard(self, card, ease):
    if ease == 1 and remem.conf.get("reschedule_siblings_on_again",False):
        if card.ivl>=21: return #avoid Lapse new ivl option

        conf=mw.col.decks.confForDid(card.did)
        if not card.odid or conf['resched']:
            cids=[i for i in mw.col.db.list(
                "select id from cards where nid=? and type=2 and queue=2 and id!=? and ivl > ?",
                card.nid, card.id, remem.conf.get("sibling_boundary",365))]
            L=len(cids)
            if L > 0:
                am=ok=remem.conf.get("automatic_mode",False)
                if not am:
                    t,ok=getText("You have %d sibling(s) out of bound, reschedule them?"%L, default=str(cids))
                if am or ok:
                    dMin=remem.conf.get("sibling_days_min",7)
                    dMax=remem.conf.get("sibling_days_max",20)
                    log=remem.conf.get("revlog_rescheduled",True)
                    customReschedCards(cids,dMin,dMax,log)


# Replace scheduler.reschedCards called by browser
def reschedCards(self, ids, imin, imax, _old):
    browConf=remem.conf.get("browser",{})
    if not browConf.get("replace_brower_reschedule",False):
        return _old(self, ids, imin, imax)
    mw.requireReset()
    log=remem.conf.get("revlog_rescheduled",True)
    runHook('ReMemorize.rescheduleAll',ids,imin,imax,log)


# Replace scheduler.forgetCards called by browser
def forgetCards(self, ids, _old):
    browConf=remem.conf.get("browser",{})
    if not browConf.get("replace_brower_reschedule",False):
        return _old(self, ids)
    mw.requireReset()
    log=remem.conf.get("revlog_rescheduled",True)
    runHook('ReMemorize.forgetAll',ids,log)


# Replaces reposition in browser so it changes the due date instead of changing the position of new cards.
def reposition(self, _old):
    browConf=remem.conf.get("browser",{})
    if not browConf.get("replace_brower_reposition",False):
        return _old(self)
    sel = self.selectedCards() #mixed selection

    if browConf.get("skip_new_card_types_on_reposition",False):
        newType = self.col.db.list(
            "select id from cards where type = 0 and id in " + ids2str(sel))
        if newType: #Change position of new cards
            return _old(self)

    d = QDialog(self)
    d.setWindowModality(Qt.WindowModal)
    frm = aqt.forms.reposition.Ui_Dialog()
    frm.setupUi(d)
    txt = _("Reschedule due date:")
    frm.label.setText(txt)
    if not d.exec_():
        return
    self.model.beginReset()
    self.mw.checkpoint(_("Rescheduled"))
    self.mw.requireReset()

    mw.progress.start()
    start=frm.start.value()
    step=frm.step.value()
    shuffle=frm.randomize.isChecked()
    shift=frm.shift.isChecked()
    for cid in sel:
        card=mw.col.getCard(cid)
        if shuffle:
            due=random.randint(start,start+step)
            remem.changeDue(card,due)
        else:
            remem.changeDue(card,start)

        if shift: start+=step
    mw.progress.finish()

    if ANKI21:
        self.search()
    else:
        self.onSearch(reset=False)
    self.model.endReset()



anki.sched.Scheduler.answerCard = wrap(anki.sched.Scheduler.answerCard, answerCard, 'after')
anki.sched.Scheduler.reschedCards = wrap(anki.sched.Scheduler.reschedCards, reschedCards, 'around')
anki.sched.Scheduler.forgetCards = wrap(anki.sched.Scheduler.forgetCards, forgetCards, 'around')
aqt.browser.Browser.reposition = wrap(aqt.browser.Browser.reposition, reposition, 'around')
if ANKI21:
    import anki.schedv2
    anki.schedv2.Scheduler.answerCard = wrap(anki.schedv2.Scheduler.answerCard, answerCard, 'after')
    anki.schedv2.Scheduler.reschedCards = wrap(anki.schedv2.Scheduler.reschedCards, reschedCards, 'around')
    anki.schedv2.Scheduler.forgetCards = wrap(anki.schedv2.Scheduler.forgetCards, forgetCards, 'around')
    aqt.browser.Browser._reposition = wrap(aqt.browser.Browser._reposition, reposition, 'around')


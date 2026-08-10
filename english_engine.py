from __future__ import annotations
from dataclasses import dataclass, asdict
import re
from dictionary_db import DictionaryDB
from volapuk_morphology import noun_case, verb_form, PRON

@dataclass
class SentenceResult:
    source: str
    english: str
    output: str
    status: str
    issues: list[str]
    evidence: list[dict]

class EnglishToVolapuk:
    def __init__(self, db: DictionaryDB):
        self.db=db
        self._nlp=None

    def nlp(self):
        if self._nlp is None:
            try:
                import spacy
                self._nlp=spacy.load("en_core_web_sm")
            except Exception:
                self._nlp=False
        return self._nlp

    def split_sentences(self,text):
        nlp=self.nlp()
        if nlp:
            doc=nlp(text)
            return [s.text.strip() for s in doc.sents if s.text.strip()]
        return [x.strip() for x in re.split(r'(?<=[.!?])\s+',text) if x.strip()]

    def unique_lex(self,lemma,pos=None):
        cs=self.db.lookup(lemma,pos)
        # A = locally curated, X2 = locally cross-confirmed, R = exact unique
        # match from the official remote dictionary. Remote candidates are only
        # trusted when the Volapük form is unique for the requested lemma/POS.
        trusted=[c for c in cs if c.grade in {"A","X2","R"} and c.confidence>=0.80]
        forms={c.volapuk for c in trusted}
        if len(forms)==1:
            # Prefer local evidence when the same form occurs in several layers.
            trusted.sort(key=lambda c: ({"A":3,"X2":2,"R":1}.get(c.grade,0),c.confidence), reverse=True)
            return trusted[0],None
        if not trusted:return None,f"no trusted dictionary entry for {lemma!r} ({pos or 'any POS'})"
        return None,f"multiple trusted senses for {lemma!r}: "+", ".join(sorted(forms))

    def _person(self,subj):
        low=subj.lemma_.lower()
        if low in {"i"}:return "ob"
        if low=="we":return "obs"
        if low=="you":return "ol"
        if low=="he":return "om"
        if low=="she":return "of"
        if low=="it":return "on"
        if low=="they":return "ons"
        if subj.pos_=="PROPN":return None
        return "on" if subj.tag_ in {"NN","NNP"} else "ons"

    def _tense(self,root):
        aux=[c for c in root.children if c.dep_ in {"aux","auxpass"}]
        auxlem={c.lemma_.lower() for c in aux}
        if "will" in auxlem:return "future"
        if "have" in auxlem and root.tag_ in {"VBN"}:
            if any(c.tag_=="VBD" and c.lemma_.lower()=="have" for c in aux):return "pluperfect"
            return "perfect"
        if root.tag_=="VBD":return "past"
        return "present"

    def translate_sentence(self,sentence):
        nlp=self.nlp()
        if not nlp:
            return SentenceResult(sentence,sentence,"","HOLD",["spaCy model en_core_web_sm is not installed."],[])
        doc=nlp(sentence)
        roots=[t for t in doc if t.dep_=="ROOT"]
        if len(roots)!=1:
            return SentenceResult(sentence,sentence,"","HOLD",["cannot identify one clause root"],[])
        root=roots[0]
        evidence=[];issues=[]
        clause_deps={"ccomp","xcomp","advcl","relcl","acl"}
        if any(t.dep_ in clause_deps for t in doc):
            return SentenceResult(sentence,sentence,"","HOLD",["embedded/relative clause requires a reviewed Volapük clause transformation"],[])

        subject=next((t for t in doc if t.dep_ in {"nsubj","nsubjpass"}),None)
        if subject is None:
            return SentenceResult(sentence,sentence,"","HOLD",["explicit subject not found"],[])
        person=self._person(subject)
        if person is None:
            issues.append("proper-name subject requires gender/person agreement review")
            person="on"

        passive=subject.dep_=="nsubjpass" or any(t.dep_=="auxpass" for t in doc)
        question=sentence.rstrip().endswith("?")
        negative=any(t.dep_=="neg" for t in doc)
        tense=self._tense(root)

        if root.lemma_.lower()=="be":
            pred=next((t for t in doc if t.dep_ in {"attr","acomp","oprd"}),None)
            if pred is None:
                return SentenceResult(sentence,sentence,"","HOLD",["unsupported copular complement"],[])
            vf=verb_form("binön",person,tense,negative,question,passive=False)
            out=[]
            if subject.pos_ not in {"PRON"}:
                sc,err=self.unique_lex(subject.lemma_.lower(),"NOUN")
                if err:issues.append(err)
                else:
                    out.append(noun_case(sc.volapuk,"nom",subject.tag_ in {"NNS","NNPS"}))
                    evidence.append(asdict(sc))
            if pred.pos_=="ADJ":
                pc,err=self.unique_lex(pred.lemma_.lower(),"ADJ")
                if err:issues.append(err)
                else:
                    out += [vf,pc.volapuk];evidence.append(asdict(pc))
            elif pred.pos_ in {"NOUN","PROPN"}:
                pc,err=self.unique_lex(pred.lemma_.lower(),"NOUN")
                if err:issues.append(err)
                else:
                    out += [vf,noun_case(pc.volapuk,"nom",pred.tag_ in {"NNS","NNPS"})];evidence.append(asdict(pc))
            else:issues.append("unsupported copular POS "+pred.pos_)
            status="HOLD" if issues else "READY"
            return SentenceResult(sentence,sentence,(" ".join(out).capitalize()+("." if not question else "?")) if out else "",status,issues,evidence)

        vc,err=self.unique_lex(root.lemma_.lower(),"VERB")
        if err:
            return SentenceResult(sentence,sentence,"","HOLD",[err],[])
        evidence.append(asdict(vc))
        vf=verb_form(vc.volapuk,person,tense,negative,question,passive)
        parts=[]

        if subject.pos_ not in {"PRON"}:
            sc,er=self.unique_lex(subject.lemma_.lower(),"NOUN")
            if er:issues.append(er)
            else:
                parts.append(noun_case(sc.volapuk,"nom",subject.tag_ in {"NNS","NNPS"}))
                evidence.append(asdict(sc))
        parts.append(vf)

        obj=next((t for t in doc if t.dep_ in {"dobj","obj"}),None)
        if obj:
            oc,er=self.unique_lex(obj.lemma_.lower(),"NOUN")
            if er:issues.append(er)
            else:
                form=noun_case(oc.volapuk,"acc",obj.tag_ in {"NNS","NNPS"})
                for a in obj.children:
                    if a.dep_=="amod":
                        ac,ae=self.unique_lex(a.lemma_.lower(),"ADJ")
                        if ae:issues.append(ae)
                        else:form+=" "+ac.volapuk;evidence.append(asdict(ac))
                parts.append(form);evidence.append(asdict(oc))

        iobj=next((t for t in doc if t.dep_ in {"iobj","dative"} and t.pos_ in {"NOUN","PROPN","PRON"}),None)
        if iobj:
            if iobj.pos_=="PRON":
                p=PRON.get(iobj.lemma_.lower())
                if p: parts.append(p[:-1]+"e" if p.endswith("i") else p+"e")
                else:issues.append("unsupported indirect pronoun "+iobj.text)
            else:
                ic,er=self.unique_lex(iobj.lemma_.lower(),"NOUN")
                if er:issues.append(er)
                else:parts.append(noun_case(ic.volapuk,"dat",iobj.tag_ in {"NNS","NNPS"}));evidence.append(asdict(ic))

        prepmap={"in":"in","at":"in","with":"ko","about":"dö","from":"de","by":"fa" if passive else "me"}
        for prep in [t for t in doc if t.dep_=="prep"]:
            pobj=next((c for c in prep.children if c.dep_=="pobj"),None)
            if not pobj:continue
            pl=prep.lemma_.lower()
            if pl=="to":
                v="lü"
            elif pl in prepmap:v=prepmap[pl]
            else:
                issues.append("unsupported preposition "+prep.text);continue
            if pobj.pos_=="PRON":
                val=PRON.get(pobj.lemma_.lower())
                if not val:issues.append("unsupported pronoun "+pobj.text);continue
                parts.append(v+" "+val)
            else:
                pc,er=self.unique_lex(pobj.lemma_.lower(),"NOUN")
                if er:issues.append(er)
                else:parts.append(v+" "+noun_case(pc.volapuk,"nom",pobj.tag_ in {"NNS","NNPS"}));evidence.append(asdict(pc))

        for a in [t for t in doc if t.pos_=="ADV" and t.dep_ in {"advmod","npadvmod"}]:
            if a.lemma_.lower() in {"not"}:continue
            ac,er=self.unique_lex(a.lemma_.lower(),"ADV")
            if er:issues.append(er)
            else:parts.append(ac.volapuk);evidence.append(asdict(ac))

        for t in doc:
            if t.pos_=="PROPN":
                issues.append("proper name unresolved: "+t.text)
            if t.dep_ in clause_deps:
                issues.append("clausal dependency: "+t.dep_)

        status="HOLD" if issues else "READY"
        out=" ".join(parts)
        if out:out=out[0].upper()+out[1:]+("?" if question else ".")
        return SentenceResult(sentence,sentence,out,status,issues,evidence)

    def translate_text(self,text):
        results=[self.translate_sentence(s) for s in self.split_sentences(text)]
        status="READY" if results and all(r.status=="READY" for r in results) else "HOLD"
        return status,results

PRON = {
 "i":"ob","we":"obs","you":"ol","he":"om","she":"of","it":"on","they":"ons",
 "me":"obi","us":"obis","him":"omi","her":"ofi","them":"onis"
}

def noun_case(root,kase="nom",plural=False):
    ending={"nom":"","gen":"a","dat":"e","acc":"i"}[kase]
    return root+ending+("s" if plural else "")

def verb_stem(inf):
    return inf[:-2] if inf.endswith("ön") else inf

def verb_form(inf,person="on",tense="present",negative=False,question=False,passive=False,conditional=False):
    pref={"present":"","perfect":"e","past":"ä","pluperfect":"i","future":"o",
          "futurePerfect":"u","futurePast":"ö","futurePastPerfect":"ü"}[tense]
    if passive: pref="pa" if tense=="present" else "p"+pref
    x=pref+verb_stem(inf)+person
    if conditional:x+="öv"
    if question:x+="-li"
    if negative:x="no "+x
    return x

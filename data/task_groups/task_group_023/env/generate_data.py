#!/usr/bin/env python3
"""Deterministically generate and validate the Observatory SQLite database."""
from __future__ import annotations
import argparse, hashlib, json, math, os, random, sqlite3, tempfile
from pathlib import Path

SEED=23072026
VERSION="1.0.0"
R=random.Random(SEED)
ROOT=Path(__file__).resolve().parent

STATE_TEXT="""01|AL|Alabama|South|East South Central
02|AK|Alaska|West|Pacific
04|AZ|Arizona|West|Mountain
05|AR|Arkansas|South|West South Central
06|CA|California|West|Pacific
08|CO|Colorado|West|Mountain
09|CT|Connecticut|Northeast|New England
10|DE|Delaware|South|South Atlantic
11|DC|District of Columbia|South|South Atlantic
12|FL|Florida|South|South Atlantic
13|GA|Georgia|South|South Atlantic
15|HI|Hawaii|West|Pacific
16|ID|Idaho|West|Mountain
17|IL|Illinois|Midwest|East North Central
18|IN|Indiana|Midwest|East North Central
19|IA|Iowa|Midwest|West North Central
20|KS|Kansas|Midwest|West North Central
21|KY|Kentucky|South|East South Central
22|LA|Louisiana|South|West South Central
23|ME|Maine|Northeast|New England
24|MD|Maryland|South|South Atlantic
25|MA|Massachusetts|Northeast|New England
26|MI|Michigan|Midwest|East North Central
27|MN|Minnesota|Midwest|West North Central
28|MS|Mississippi|South|East South Central
29|MO|Missouri|Midwest|West North Central
30|MT|Montana|West|Mountain
31|NE|Nebraska|Midwest|West North Central
32|NV|Nevada|West|Mountain
33|NH|New Hampshire|Northeast|New England
34|NJ|New Jersey|Northeast|Middle Atlantic
35|NM|New Mexico|West|Mountain
36|NY|New York|Northeast|Middle Atlantic
37|NC|North Carolina|South|South Atlantic
38|ND|North Dakota|Midwest|West North Central
39|OH|Ohio|Midwest|East North Central
40|OK|Oklahoma|South|West South Central
41|OR|Oregon|West|Pacific
42|PA|Pennsylvania|Northeast|Middle Atlantic
44|RI|Rhode Island|Northeast|New England
45|SC|South Carolina|South|South Atlantic
46|SD|South Dakota|Midwest|West North Central
47|TN|Tennessee|South|East South Central
48|TX|Texas|South|West South Central
49|UT|Utah|West|Mountain
50|VT|Vermont|Northeast|New England
51|VA|Virginia|South|South Atlantic
53|WA|Washington|West|Pacific
54|WV|West Virginia|South|South Atlantic
55|WI|Wisconsin|Midwest|East North Central
56|WY|Wyoming|West|Mountain"""
STATES=[tuple(x.split("|")) for x in STATE_TEXT.splitlines()]
STATE_MEASURES=["life_expectancy","adult_obesity","diagnosed_diabetes","physical_inactivity","food_insecurity","frequent_mental_distress","premature_mortality_rate","adult_smoking"]
COUNTY_MEASURES=["adult_obesity","physical_inactivity","diagnosed_diabetes","depression","short_sleep","severe_housing_cost_burden","copd","adult_smoking"]
COUNTRY_INDICATORS=["life_expectancy","adult_mortality","infant_mortality","bmi_burden","immunization_gap","schooling_gap","poverty_rate","health_spending_gap","alcohol_harm","hiv_burden","unemployment","urbanization"]

SCHEMA="""
PRAGMA foreign_keys=ON;
CREATE TABLE geo_state(state_fips TEXT PRIMARY KEY,state_abbr TEXT UNIQUE,state_name TEXT,region TEXT CHECK(region IN('Northeast','Midwest','South','West')),division TEXT,is_state INTEGER);
CREATE TABLE geo_county(county_fips TEXT PRIMARY KEY,state_fips TEXT REFERENCES geo_state,state_abbr TEXT,county_name TEXT,rucc INTEGER CHECK(rucc BETWEEN 1 AND 9),metro_class TEXT CHECK(metro_class IN('METRO','NONMETRO')),population_base INTEGER,latitude REAL,longitude REAL);
CREATE TABLE geo_country(iso3 TEXT PRIMARY KEY,canonical_name TEXT,portal_label TEXT,alternate_labels TEXT,region TEXT,income_group TEXT CHECK(income_group IN('HIGH','UPPER_MIDDLE','LOWER_MIDDLE','LOW')));
CREATE TABLE measure_dictionary(domain TEXT,measure_id TEXT,display_name TEXT,unit TEXT,direction TEXT CHECK(direction IN('HIGHER_BETTER','HIGHER_WORSE','NEUTRAL')),default_publication_value_type TEXT,valid_min REAL,valid_max REAL,description TEXT,PRIMARY KEY(domain,measure_id));
CREATE TABLE state_health_observation(observation_id TEXT PRIMARY KEY,state_fips TEXT REFERENCES geo_state,state_abbr TEXT,year INTEGER,measure_id TEXT,value_type TEXT CHECK(value_type IN('CRUDE','AGE_ADJUSTED')),source_type TEXT CHECK(source_type IN('DIRECT_SURVEY','COUNTY_ROLLUP')),release_status TEXT CHECK(release_status IN('FINAL','PROVISIONAL')),revision INTEGER,value REAL,standard_error REAL,sample_size INTEGER,suppression_flag INTEGER,quality_flag TEXT,released_at TEXT);
CREATE TABLE state_socioeconomic(record_id TEXT PRIMARY KEY,state_fips TEXT REFERENCES geo_state,state_abbr TEXT,year INTEGER,release_status TEXT,revision INTEGER,released_at TEXT,poverty REAL,bachelors REAL,median_income REAL,unemployment REAL,uninsured REAL,food_insecurity REAL,population INTEGER,quality_flag TEXT);
CREATE TABLE county_health_observation(observation_id TEXT PRIMARY KEY,county_fips TEXT REFERENCES geo_county,state_abbr TEXT,year INTEGER,measure_id TEXT,value_type TEXT CHECK(value_type IN('CRUDE','AGE_ADJUSTED')),release_status TEXT,revision INTEGER,released_at TEXT,value REAL,low_ci REAL,high_ci REAL,population INTEGER,suppression_flag INTEGER,quality_flag TEXT);
CREATE TABLE county_socioeconomic(record_id TEXT PRIMARY KEY,county_fips TEXT REFERENCES geo_county,state_abbr TEXT,year INTEGER,release_status TEXT,revision INTEGER,released_at TEXT,poverty REAL,median_income REAL,bachelors REAL,unemployment REAL,net_migration REAL,uninsured REAL,population INTEGER,quality_flag TEXT);
CREATE TABLE country_indicator_observation(observation_id TEXT PRIMARY KEY,country_label TEXT,iso3 TEXT,year INTEGER,indicator_id TEXT,release_status TEXT,revision INTEGER,released_at TEXT,value REAL,unit TEXT,quality_flag TEXT);
CREATE TABLE revision_event(revision_event_id TEXT PRIMARY KEY,domain TEXT CHECK(domain IN('STATE_HEALTH','STATE_SES','COUNTY_HEALTH','COUNTY_SES','COUNTRY')),entity_id TEXT,field_id TEXT,effective_year INTEGER,old_value REAL,new_value REAL,status TEXT CHECK(status IN('APPLIED','WITHDRAWN','PENDING')),issued_at TEXT,reason_code TEXT CHECK(reason_code IN('SCALE_CORRECTION','SOURCE_RESTATE','LATE_RESPONSE','GEOGRAPHY_RECODE')),note TEXT);
CREATE TABLE methodology_document(doc_id TEXT PRIMARY KEY,title TEXT,version TEXT,effective_date TEXT,status TEXT CHECK(status IN('CURRENT','SUPERSEDED','DRAFT')),topic TEXT,body TEXT);
"""

def bounded(x,a,b): return round(max(a,min(b,x)),3)
def date(year,month=8,day=15): return f"{year:04d}-{month:02d}-{day:02d}"
def shuffled_insert(c,table,cols,rows):
    R.shuffle(rows); c.executemany(f"INSERT INTO {table}({','.join(cols)}) VALUES({','.join('?' for _ in cols)})",rows)
def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
    return h.hexdigest()
def atomic_json(path,obj):
    tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8"); os.replace(tmp,path)

def build(db):
    global R; R=random.Random(SEED)
    c=sqlite3.connect(db); c.executescript(SCHEMA)
    c.executemany("INSERT INTO geo_state VALUES(?,?,?,?,?,?)",[(f,a,n,r,d,0 if a=="DC" else 1) for f,a,n,r,d in STATES])
    latents={}; counties=[]; county_lat={}
    stems=["Alder","Birch","Cedar","Dover","Elm","Fairview","Glen","Harbor","Ivy","Juniper","King","Lake","Maple","Northfield","Oak","Pine","Quartz","River","Summit","Timber","Union","Valley","Willow","York"]
    region_center={"Northeast":(42,-73),"Midwest":(42,-91),"South":(34,-84),"West":(39,-116)}
    for si,(f,a,n,region,division) in enumerate(STATES):
        advantage=R.gauss(0,1)+(0.35 if region=="Northeast" else -0.25 if region=="South" else 0)
        risk=R.gauss(0,1)-.35*advantage; access=R.gauss(0,1)+.45*advantage
        if a in ("DC","WV","MS","AK"): risk += {"DC":-1.0,"WV":1.5,"MS":1.1,"AK":.6}[a]
        latents[a]=(advantage,risk,access)
        for j in range(24):
            suffix=f"{2*j+1:03d}"; cf=f+suffix
            rural=R.random(); pop=int(max(2400,math.exp(R.gauss(10.15-1.7*rural,.72))))
            rucc=max(1,min(9,int(1+rural*9+(1 if pop<15000 else -1 if pop>150000 else 0))))
            metro="METRO" if rucc<=3 else "NONMETRO"
            name=f"{stems[(j+si*5)%len(stems)]} County"
            rc=region_center[region]
            counties.append((cf,f,a,name,rucc,metro,pop,round(rc[0]+R.uniform(-5,5),4),round(rc[1]+R.uniform(-7,7),4)))
            county_lat[cf]=(advantage+R.gauss(0,.55)-.1*(rucc-3),risk+R.gauss(0,.6)+.08*(rucc-3),access+R.gauss(0,.55)-.1*(rucc-3),pop,rucc,a)
    shuffled_insert(c,"geo_county",["county_fips","state_fips","state_abbr","county_name","rucc","metro_class","population_base","latitude","longitude"],counties)
    roots=["Alder","Bracken","Cobalt","Doria","Estel","Faron","Galen","Haven","Ionia","Jura","Kestral","Lumen","Maren","Noria","Orin","Pavia","Quilla","Roven"]
    forms=["Republic","Federation","Isles","Union"]
    regions=["Africa","Americas","Asia","Europe","Oceania","Middle East"]
    countries=[]; country_lat={}
    for i in range(72):
        iso="Q"+chr(65+i//26)+chr(65+i%26); root=roots[i%len(roots)]; form=forms[(i//18)%4]
        canon=f"{root} {form}"; label=(f"Republic of {root}" if i<14 else canon); aliases=f"{canon}|{root}|{label}"
        region=regions[i%6]; dev=R.gauss(0,1)+(0.7 if region=="Europe" else -.45 if region=="Africa" else 0); system=R.gauss(0,1)+.6*dev; infectious=R.gauss(0,1)-.7*dev; behavior=R.gauss(0,1)+.15*dev
        income="HIGH" if dev>.75 else "UPPER_MIDDLE" if dev>0 else "LOWER_MIDDLE" if dev>-.8 else "LOW"
        countries.append((iso,canon,label,aliases,region,income)); country_lat[iso]=(dev,system,infectious,behavior,label,canon)
    shuffled_insert(c,"geo_country",["iso3","canonical_name","portal_label","alternate_labels","region","income_group"],countries)
    dictionary=[]
    for domain,measures in (("STATE_HEALTH",STATE_MEASURES),("COUNTY_HEALTH",COUNTY_MEASURES),("COUNTRY",COUNTRY_INDICATORS)):
        for m in measures:
            unit="years" if m=="life_expectancy" else "deaths per 100,000" if m in ("premature_mortality_rate","adult_mortality") else "deaths per 1,000" if m=="infant_mortality" else "percent"
            direction="HIGHER_BETTER" if m=="life_expectancy" else "NEUTRAL" if m=="urbanization" else "HIGHER_WORSE"
            lo,hi=(50,90) if m=="life_expectancy" else (150,700) if m=="premature_mortality_rate" else (0,100)
            dictionary.append((domain,m,m.replace("_"," ").title(),unit,direction,"CRUDE" if domain=="COUNTY_HEALTH" else "AGE_ADJUSTED",lo,hi,f"Published {m.replace('_',' ')} measure with release and revision metadata."))
    shuffled_insert(c,"measure_dictionary",["domain","measure_id","display_name","unit","direction","default_publication_value_type","valid_min","valid_max","description"],dictionary)
    docs=[
      ("release-lifecycle","Surveillance release lifecycle","3.1","2024-01-15","CURRENT","releases","Provisional records support timely review. Final records replace provisional records for publication, and the highest applied final revision governs when several final revisions exist."),
      ("release-lifecycle-v2","Earlier surveillance release lifecycle","2.0","2021-02-01","SUPERSEDED","releases","This earlier policy treated the first final file as closed. Later policy permits documented final revisions."),
      ("state-estimates","State direct and rollup estimates","2.2","2024-03-10","CURRENT","state health","Direct survey estimates are the primary state publication series. County rollups are parallel estimates for coverage review and should not silently replace direct records."),
      ("publication-values","Crude and age-adjusted publication use","2.4","2023-11-05","CURRENT","value types","Age-adjusted values support state comparisons where specified. Crude values describe observed county burden and retain the population structure of each county."),
      ("geographic-ids","Geographic identifiers","1.8","2024-02-20","CURRENT","geography","State and county FIPS identifiers are text. Leading zeros are meaningful, and county identifiers contain the two-character state code followed by a three-character county suffix."),
      ("suppression","Small-number suppression","4.0","2024-04-01","CURRENT","suppression","Suppressed observations retain identifying and release metadata but do not publish a value. Analysts must not treat a suppressed or missing value as zero."),
      ("socioeconomic-fields","Socioeconomic release fields","3.0","2024-05-17","CURRENT","socioeconomic","Socioeconomic fields are revised independently after late responses. Sparse null fields do not invalidate other published fields in the same record."),
      ("rucc","Rural-Urban Continuum Codes","1.6","2023-07-12","CURRENT","RUCC","RUCC values one through three are metropolitan in this portal; four through nine are nonmetropolitan. RUCC belongs to the county geography reference."),
      ("influence","Influence diagnostics guidance","2.1","2024-06-10","CURRENT","statistics","Influence diagnostics assess how strongly fitted results depend on individual observations. Findings should report the declared model, eligible record set, and the effect of any sensitivity exclusion."),
      ("country-revisions","Country indicator revision notices","2.7","2024-08-22","CURRENT","country revisions","Applied scale corrections appear in later final revisions. Pending or withdrawn notices do not authorize replacement, and portal labels should be reconciled to stable country identifiers."),
      ("indicator-direction","Indicator direction and units","3.3","2024-09-01","CURRENT","country indicators","The dictionary declares whether higher values are favorable, unfavorable, or neutral. Units must be checked before combining indicators; percentages and mortality rates are not interchangeable."),
      ("aliases","Country label reconciliation","1.4","2023-06-02","CURRENT","country labels","Portal labels can differ from canonical names. Stable ISO3-like identifiers and the alternate-label reference support reconciliation across releases."),
      ("quality","Quality flag interpretation","1.2","2024-07-08","CURRENT","quality","Quality flags describe review state and do not change release precedence. A stale or caution flag should be retained in audit extracts."),
      ("revisions-draft","Draft revision consultation","0.9","2025-01-10","DRAFT","releases","This draft proposes a longer public review interval for source restatements. It does not supersede current publication policy."),
      ("county-windows","County socioeconomic comparability","1.5","2024-10-14","CURRENT","socioeconomic","Comparisons across years use like-for-like final fields. Population and net migration are separately released, and a later year may increase or decrease relative to an earlier year.")]
    shuffled_insert(c,"methodology_document",["doc_id","title","version","effective_date","status","topic","body"],docs)
    noise={"seed":SEED,"generator_version":VERSION,"categories":{}}
    sh=[]; ss=[]; ch=[]; cs=[]; ci=[]; revisions=[]
    ids={"sh":0,"ss":0,"ch":0,"cs":0,"ci":0,"rv":0}
    def newid(kind): ids[kind]+=1; return f"{kind.upper()}{ids[kind]:08d}"
    def state_value(m,adv,risk,access,year):
        trend=year-2020; e=R.gauss(0,1)
        vals={"life_expectancy":76.8+1.35*adv-1.25*risk+.25*access+.12*trend+.55*e,
        "adult_obesity":31.5+2.5*risk-1.2*adv-.25*trend+1.1*e,"diagnosed_diabetes":10.2+1.15*risk-.65*adv-.08*trend+.55*e,
        "physical_inactivity":23+2.4*risk-1.5*adv-.2*trend+1.0*e,"food_insecurity":12.5+2.1*risk-2.0*adv-.18*trend+.9*e,
        "frequent_mental_distress":14.2+1.5*risk-.5*access+.12*trend+.8*e,"premature_mortality_rate":380+48*risk-34*adv-6*trend+17*e,
        "adult_smoking":17+2.3*risk-1.0*adv-.35*trend+.8*e}
        return bounded(vals[m],55 if m=="life_expectancy" else 180 if m=="premature_mortality_rate" else 1,84 if m=="life_expectancy" else 650 if m=="premature_mortality_rate" else 55)
    suppressed_state=0; collision_state=0
    for f,a,n,region,division in STATES:
        adv,risk,access=latents[a]; basepop=int(math.exp(R.gauss(15.2,.55)))
        for year in range(2020,2025):
            ses=[bounded(14-3*adv+1.2*risk-.15*(year-2020)+R.gauss(0,.7),3,28),bounded(32+7*adv+R.gauss(0,1.5),14,62),bounded(61000+14500*adv+3500*(year-2020)+R.gauss(0,3500),30000,135000),bounded(5.4-1.1*adv+.5*risk+R.gauss(0,.35),2,13),bounded(8.5-1.7*adv-.25*(year-2020)+R.gauss(0,.5),2,18),bounded(12.5-1.9*adv+1.2*risk+R.gauss(0,.6),3,25)]
            if R.random()<.08: ses[R.randrange(6)]=None
            row=[newid("ss"),f,a,year,"FINAL",1,date(year+1,9,20),*ses,int(basepop*(1+.006*(year-2020))),"REVIEWED"]
            ss.append(tuple(row))
            if R.random()<.18:
                old=[None if v is None else round(v+R.gauss(0,.6 if i!=2 else 1200),3) for i,v in enumerate(ses)]
                ss.append((newid("ss"),f,a,year,"PROVISIONAL",0,date(year+1,4,10),*old,int(basepop*(1+.005*(year-2020))),"PROVISIONAL")); collision_state+=1
            if R.random()<.07:
                revised=list(ses); k=R.randrange(6)
                if revised[k] is not None: revised[k]=round(revised[k]+R.gauss(0,.3 if k!=2 else 700),3)
                ss.append((newid("ss"),f,a,year,"FINAL",2,date(year+1,11,5),*revised,int(basepop*(1+.006*(year-2020))),"REVISED")); collision_state+=1
            for m in STATE_MEASURES:
                for vt in ("CRUDE","AGE_ADJUSTED"):
                    val=state_value(m,adv,risk,access,year)+(R.gauss(0,.3) if vt=="CRUDE" else R.gauss(0,.18))
                    val=bounded(val,55 if m=="life_expectancy" else 180 if m=="premature_mortality_rate" else 0,84 if m=="life_expectancy" else 650 if m=="premature_mortality_rate" else 100)
                    supp=R.random() < (.035+.035*(m in ("frequent_mental_distress","diagnosed_diabetes"))+.02*(year==2020))
                    if supp: val=None; suppressed_state+=1
                    se=round((.18 if m=="life_expectancy" else 7 if m=="premature_mortality_rate" else .45)*R.uniform(.8,1.4),3)
                    sh.append((newid("sh"),f,a,year,m,vt,"DIRECT_SURVEY","FINAL",1,val,se,R.randint(1200,15000),int(supp),"SUPPRESSED" if supp else "REVIEWED",date(year+1,8,15)))
                    if R.random()<.06:
                        pv=None if val is None else round(val+R.gauss(0,se),3)
                        sh.append((newid("sh"),f,a,year,m,vt,"DIRECT_SURVEY","PROVISIONAL",0,pv,se*1.1,R.randint(900,12000),int(supp),"PROVISIONAL",date(year+1,3,10))); collision_state+=1
                    if R.random()<.035:
                        rv=None if val is None else round(val+R.gauss(0,se*.25),3)
                        sh.append((newid("sh"),f,a,year,m,vt,"DIRECT_SURVEY","FINAL",2,rv,se,R.randint(1200,15000),int(supp),"REVISED",date(year+1,11,20))); collision_state+=1
                    if vt=="CRUDE" and R.random()<.22:
                        roll=None if val is None else round(val+R.gauss(0,se*.8),3)
                        sh.append((newid("sh"),f,a,year,m,vt,"COUNTY_ROLLUP","FINAL",1,roll,se*1.2,R.randint(10000,90000),int(supp),"PARALLEL_ESTIMATE",date(year+1,10,1)))
    suppressed_county=0; missing_county=0; collision_county=0
    for cf,(adv,risk,access,pop0,rucc,a) in county_lat.items():
        for year in range(2020,2025):
            pop=int(pop0*(1+R.uniform(-.006,.014)*(year-2020)))
            vals=[bounded(15.5-3.4*adv+1.4*risk+R.gauss(0,1.3),2,38),bounded(57000+12500*adv-1200*rucc+1800*(year-2020)+R.gauss(0,5000),22000,145000),bounded(27+7*adv-1.1*rucc+R.gauss(0,2.2),8,65),bounded(5.8-1.2*adv+.45*risk+R.gauss(0,.65),1.5,18),bounded(R.gauss(0,7)+1.2*adv-.7*rucc,-30,30),bounded(9.5-1.7*adv+.45*rucc+R.gauss(0,.8),1,30)]
            if R.random()<.07: vals[R.randrange(6)]=None
            cs.append((newid("cs"),cf,a,year,"FINAL",1,date(year+1,9,28),*vals,pop,"REVIEWED"))
            if R.random()<.08:
                old=[None if v is None else round(v+R.gauss(0,.6 if i!=1 else 1800),3) for i,v in enumerate(vals)]
                cs.append((newid("cs"),cf,a,year,"PROVISIONAL",0,date(year+1,4,12),*old,pop,"PROVISIONAL")); collision_county+=1
            if R.random()<.025:
                new=list(vals); k=R.randrange(6)
                if new[k] is not None: new[k]=round(new[k]+R.gauss(0,.3 if k!=1 else 900),3)
                cs.append((newid("cs"),cf,a,year,"FINAL",2,date(year+1,11,8),*new,pop,"REVISED")); collision_county+=1
        for year in range(2021,2025):
            pop=int(pop0*(1+R.uniform(-.005,.012)*(year-2020)))
            for m in COUNTY_MEASURES:
                if R.random()<.045: missing_county+=1; continue
                types=["CRUDE"]+(["AGE_ADJUSTED"] if R.random()<.24 else [])
                for vt in types:
                    e=R.gauss(0,1); base={"adult_obesity":31+2.8*risk-1.1*adv,"physical_inactivity":22+2.6*risk-1.2*adv+.25*rucc,"diagnosed_diabetes":9.5+1.3*risk-.5*adv,"depression":15+1.4*risk-.3*access,"short_sleep":33+2.0*risk-.5*adv,"severe_housing_cost_burden":14-1.6*adv+.5*risk,"copd":7+1.4*risk+.22*rucc,"adult_smoking":16+2.5*risk-.8*adv}[m]
                    val=bounded(base-.16*(year-2021)+e*(1.5 if m not in ("copd","diagnosed_diabetes") else .65)+(R.gauss(0,.35) if vt=="AGE_ADJUSTED" else 0),0,65)
                    p=min(.18,.015+150/max(pop,2500)); supp=R.random()<p
                    if supp: val=None; suppressed_county+=1
                    width=round((.65+900/math.sqrt(max(pop,1)))*R.uniform(.8,1.2),3)
                    low=None if val is None else max(0,round(val-width,3)); high=None if val is None else min(100,round(val+width,3))
                    ch.append((newid("ch"),cf,a,year,m,vt,"FINAL",1,date(year+1,8,25),val,low,high,pop,int(supp),"SUPPRESSED" if supp else "REVIEWED"))
                    if R.random()<.035:
                        pv=None if val is None else bounded(val+R.gauss(0,width*.45),0,65)
                        ch.append((newid("ch"),cf,a,year,m,vt,"PROVISIONAL",0,date(year+1,3,15),pv,None if pv is None else max(0,pv-width*1.2),None if pv is None else pv+width*1.2,pop,int(supp),"STALE" if R.random()<.18 else "PROVISIONAL")); collision_county+=1
    missing_country=0; country_collisions=0; scale_breaks=0; alias_rows=0
    break_keys={("QAA","adult_mortality",2018),("QAB","infant_mortality",2019),("QAC","poverty_rate",2020),("QAD","hiv_burden",2017),("QAE","unemployment",2021),("QAF","bmi_burden",2016),("QAG","immunization_gap",2022),("QAH","health_spending_gap",2015),("QAI","alcohol_harm",2023),("QAJ","schooling_gap",2019)}
    missing_rate={m:.08+.01*(i%6) for i,m in enumerate(COUNTRY_INDICATORS)}
    def country_value(m,dev,system,infectious,behavior,year):
        t=year-2013; e=R.gauss(0,1)
        vals={"life_expectancy":68+5.2*dev+2*system-2.1*infectious+.18*t+e,"adult_mortality":250-48*dev-27*system+35*infectious-2.5*t+12*e,"infant_mortality":25-6.2*dev-4.2*system+7*infectious-.6*t+2.3*e,"bmi_burden":20+4*dev+3*behavior+.18*t+1.4*e,"immunization_gap":19-5*dev-5*system+3*infectious-.45*t+1.5*e,"schooling_gap":18-5.5*dev-.35*t+1.4*e,"poverty_rate":24-7*dev-2*system-.5*t+2.4*e,"health_spending_gap":17-4*dev-4*system-.25*t+1.4*e,"alcohol_harm":9+2.2*behavior+1.2*dev+.08*t+1.2*e,"hiv_burden":7-1.5*dev+5*infectious-.12*t+1.1*e,"unemployment":8-1.1*dev+.4*infectious+.9*e,"urbanization":55+12*dev+.65*t+3*e}
        lo,hi=(55,84) if m=="life_expectancy" else (40,500) if m=="adult_mortality" else (0,100)
        return bounded(vals[m],lo,hi)
    for iso,(dev,system,infectious,behavior,label,canon) in country_lat.items():
        for year in range(2013,2025):
            for m in COUNTRY_INDICATORS:
                if R.random()<missing_rate[m]: missing_country+=1; continue
                val=country_value(m,dev,system,infectious,behavior,year); original=val
                broken=(iso,m,year) in break_keys
                if broken: val=round(val*10,3); scale_breaks+=1
                unit="years" if m=="life_expectancy" else "deaths per 100,000" if m=="adult_mortality" else "deaths per 1,000" if m=="infant_mortality" else "percent"
                shown=label if R.random()<.8 else canon
                if shown!=canon: alias_rows+=1
                stored_iso="" if R.random()<.012 else iso
                ci.append((newid("ci"),shown,stored_iso,year,m,"FINAL",1,date(year+1,7,15),val,unit,"SCALE_REVIEW" if broken else "REVIEWED"))
                if broken:
                    applied=iso in {"QAA","QAB","QAC","QAD","QAE"}
                    status="APPLIED" if applied else ("PENDING" if ord(iso[-1])%2 else "WITHDRAWN")
                    revisions.append((newid("rv"),"COUNTRY",iso,m,year,val,original,status,date(year+1,10,10),"SCALE_CORRECTION","Unit review identified an apparent scale discontinuity; notice status controls publication use."))
                    if applied: ci.append((newid("ci"),shown,iso,year,m,"FINAL",2,date(year+1,10,12),original,unit,"CORRECTED")); country_collisions+=1
                if R.random()<.055:
                    pv=bounded(original+R.gauss(0,1.0),55 if m=="life_expectancy" else 0,500 if m=="adult_mortality" else 100)
                    ci.append((newid("ci"),shown,stored_iso,year,m,"PROVISIONAL",0,date(year+1,3,4),pv,unit,"PROVISIONAL")); country_collisions+=1
    domains=["STATE_HEALTH","STATE_SES","COUNTY_HEALTH","COUNTY_SES","COUNTRY"]
    reasons=["SOURCE_RESTATE","LATE_RESPONSE","GEOGRAPHY_RECODE"]
    for i in range(120):
        domain=domains[i%5]; entity=(STATES[i%51][1] if domain.startswith("STATE") else counties[i%len(counties)][0] if domain.startswith("COUNTY") else countries[i%72][0])
        field=(STATE_MEASURES[i%8] if domain=="STATE_HEALTH" else COUNTY_MEASURES[i%8] if domain=="COUNTY_HEALTH" else COUNTRY_INDICATORS[i%12] if domain=="COUNTRY" else ["poverty","median_income","unemployment"][i%3])
        old=round(R.uniform(5,70),3); new=round(old+R.gauss(0,2),3); status=["APPLIED","WITHDRAWN","PENDING"][i%3]
        revisions.append((newid("rv"),domain,entity,field,2020+i%5,old,new,status,date(2021+i%5,6,1+i%20),reasons[i%3],"Routine release notice retained for the public audit trail."))
    shuffled_insert(c,"state_health_observation",["observation_id","state_fips","state_abbr","year","measure_id","value_type","source_type","release_status","revision","value","standard_error","sample_size","suppression_flag","quality_flag","released_at"],sh)
    shuffled_insert(c,"state_socioeconomic",["record_id","state_fips","state_abbr","year","release_status","revision","released_at","poverty","bachelors","median_income","unemployment","uninsured","food_insecurity","population","quality_flag"],ss)
    shuffled_insert(c,"county_health_observation",["observation_id","county_fips","state_abbr","year","measure_id","value_type","release_status","revision","released_at","value","low_ci","high_ci","population","suppression_flag","quality_flag"],ch)
    shuffled_insert(c,"county_socioeconomic",["record_id","county_fips","state_abbr","year","release_status","revision","released_at","poverty","median_income","bachelors","unemployment","net_migration","uninsured","population","quality_flag"],cs)
    shuffled_insert(c,"country_indicator_observation",["observation_id","country_label","iso3","year","indicator_id","release_status","revision","released_at","value","unit","quality_flag"],ci)
    shuffled_insert(c,"revision_event",["revision_event_id","domain","entity_id","field_id","effective_year","old_value","new_value","status","issued_at","reason_code","note"],revisions)
    indexes={"geo_county":["state_abbr","rucc","metro_class"],"geo_country":["portal_label","region","income_group"],"state_health_observation":["state_abbr","measure_id","year","value_type","source_type","release_status","revision"],"state_socioeconomic":["state_abbr","year","release_status","revision"],"county_health_observation":["county_fips","state_abbr","measure_id","year","value_type","release_status","revision","suppression_flag"],"county_socioeconomic":["county_fips","state_abbr","year","release_status","revision"],"country_indicator_observation":["iso3","country_label","indicator_id","year","release_status","revision","quality_flag"],"revision_event":["domain","entity_id","field_id","effective_year","status"]}
    for table,names in indexes.items():
        for name in names: c.execute(f"CREATE INDEX idx_{table}_{name} ON {table}({name})")
    c.commit(); c.execute("ANALYZE"); c.commit()
    noise["categories"]={"state_suppressed_rows":suppressed_state,"state_release_collisions":collision_state,"county_suppressed_rows":suppressed_county,"county_missing_base_records":missing_county,"county_release_collisions":collision_county,"country_indicator_missing_records":missing_country,"country_release_collisions":country_collisions,"country_scale_breaks":scale_breaks,"country_alias_label_rows":alias_rows,"revision_events":len(revisions)}
    c.close(); return noise

TABLES=["geo_state","geo_county","geo_country","measure_dictionary","state_health_observation","state_socioeconomic","county_health_observation","county_socioeconomic","country_indicator_observation","revision_event","methodology_document"]
YEAR_COLS={"state_health_observation":"year","state_socioeconomic":"year","county_health_observation":"year","county_socioeconomic":"year","country_indicator_observation":"year","revision_event":"effective_year"}

def validate(path):
    c=sqlite3.connect(path)
    assert c.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
    assert c.execute("PRAGMA foreign_key_check").fetchall()==[]
    present={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert set(TABLES)<=present
    expected={"geo_state":51,"geo_county":1224,"geo_country":72,"measure_dictionary":28,"methodology_document":15}
    counts={t:c.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in TABLES}
    for t,n in expected.items(): assert counts[t]==n,(t,counts[t],n)
    assert counts["county_health_observation"]>35000
    assert 9000<counts["country_indicator_observation"]<13000
    assert c.execute("SELECT count(*) FROM geo_county WHERE length(county_fips)!=5 OR substr(county_fips,-3)='000'").fetchone()[0]==0
    assert c.execute("SELECT count(*) FROM geo_country WHERE portal_label!=canonical_name").fetchone()[0]>=14
    assert c.execute("SELECT count(*) FROM state_health_observation WHERE year NOT BETWEEN 2020 AND 2024 OR value_type NOT IN('CRUDE','AGE_ADJUSTED') OR source_type NOT IN('DIRECT_SURVEY','COUNTY_ROLLUP') OR release_status NOT IN('FINAL','PROVISIONAL')").fetchone()[0]==0
    assert c.execute("SELECT count(*) FROM county_health_observation WHERE year NOT BETWEEN 2021 AND 2024 OR value_type NOT IN('CRUDE','AGE_ADJUSTED') OR release_status NOT IN('FINAL','PROVISIONAL')").fetchone()[0]==0
    assert c.execute("SELECT count(*) FROM country_indicator_observation WHERE year NOT BETWEEN 2013 AND 2024 OR release_status NOT IN('FINAL','PROVISIONAL')").fetchone()[0]==0
    assert c.execute("SELECT count(*) FROM state_health_observation WHERE value IS NOT NULL AND ((measure_id='life_expectancy' AND value NOT BETWEEN 55 AND 84) OR (measure_id='premature_mortality_rate' AND value NOT BETWEEN 180 AND 650) OR (measure_id NOT IN('life_expectancy','premature_mortality_rate') AND value NOT BETWEEN 0 AND 100))").fetchone()[0]==0
    assert c.execute("SELECT count(*) FROM county_health_observation WHERE value IS NOT NULL AND value NOT BETWEEN 0 AND 100").fetchone()[0]==0
    county_suppression=c.execute("SELECT 1.0*sum(suppression_flag)/count(*) FROM county_health_observation").fetchone()[0]
    state_suppression=c.execute("SELECT 1.0*sum(suppression_flag)/count(*) FROM state_health_observation").fetchone()[0]
    assert .03<=county_suppression<=.07,county_suppression
    assert .04<=state_suppression<=.08,state_suppression
    assert c.execute("SELECT count(*) FROM state_socioeconomic WHERE median_income IS NOT NULL AND median_income<=0").fetchone()[0]==0
    assert c.execute("SELECT count(*) FROM county_socioeconomic WHERE median_income IS NOT NULL AND median_income<=0").fetchone()[0]==0
    assert c.execute("SELECT count(DISTINCT measure_id) FROM county_health_observation WHERE value_type='CRUDE'").fetchone()[0]==8
    assert c.execute("SELECT count(*) FROM revision_event WHERE reason_code='SCALE_CORRECTION'").fetchone()[0]>=8
    assert c.execute("""SELECT count(*) FROM revision_event r WHERE r.domain='COUNTRY' AND r.reason_code='SCALE_CORRECTION' AND r.status='APPLIED' AND NOT EXISTS(SELECT 1 FROM country_indicator_observation o WHERE o.iso3=r.entity_id AND o.indicator_id=r.field_id AND o.year=r.effective_year AND o.release_status='FINAL' AND o.revision>1 AND abs(o.value-r.new_value)<.0001)""").fetchone()[0]==0
    uniqueness={}
    for t in TABLES:
        pk=[r[1] for r in c.execute(f"PRAGMA table_info({t})") if r[5]]
        if not pk: uniqueness[t]=False; continue
        joined=",".join(pk)
        total=c.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        grouped=c.execute(f"SELECT count(*) FROM (SELECT {joined} FROM {t} GROUP BY {joined})").fetchone()[0]
        unique=total==grouped
        uniqueness[t]=unique; assert unique
    coverage={t:{"min":c.execute(f"SELECT min({y}) FROM {t}").fetchone()[0],"max":c.execute(f"SELECT max({y}) FROM {t}").fetchone()[0]} for t,y in YEAR_COLS.items()}
    assert coverage["state_health_observation"]=={"min":2020,"max":2024}
    assert coverage["state_socioeconomic"]=={"min":2020,"max":2024}
    assert coverage["county_health_observation"]=={"min":2021,"max":2024}
    assert coverage["county_socioeconomic"]=={"min":2020,"max":2024}
    assert coverage["country_indicator_observation"]=={"min":2013,"max":2024}
    table_hashes={}
    for t in TABLES:
        pk=[r[1] for r in c.execute(f"PRAGMA table_info({t})") if r[5]]
        h=hashlib.sha256()
        for row in c.execute(f"SELECT * FROM {t} ORDER BY {','.join(pk)}"):
            h.update(json.dumps(row,separators=(",",":"),ensure_ascii=True).encode()); h.update(b"\n")
        table_hashes[t]=h.hexdigest()
    c.close()
    return counts,coverage,uniqueness,table_hashes

def generate(output):
    output.parent.mkdir(parents=True,exist_ok=True)
    fd,tmpname=tempfile.mkstemp(prefix="observatory-",suffix=".sqlite",dir=output.parent); os.close(fd); os.unlink(tmpname)
    tmp=Path(tmpname)
    try:
        noise=build(tmp); counts,coverage,uniqueness,table_hashes=validate(tmp)
        os.replace(tmp,output)
        noise_path=output.parent/"noise_manifest.json"; atomic_json(noise_path,noise)
        manifest={"seed":SEED,"generator_version":VERSION,"files":["observatory.sqlite","manifest.json","noise_manifest.json"],"tables":TABLES,"row_counts":counts,"min_max_years":coverage,"primary_key_uniqueness":uniqueness,"sha256":{"observatory.sqlite":sha(output),"noise_manifest.json":sha(noise_path)},"table_sha256":table_hashes}
        atomic_json(output.parent/"manifest.json",manifest)
        return manifest
    finally:
        if tmp.exists(): tmp.unlink()

def main():
    p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,default=ROOT/"generated/observatory.sqlite"); p.add_argument("--check",action="store_true"); args=p.parse_args()
    if args.check:
        counts,coverage,unique,hashes=validate(args.output); result={"status":"ok","seed":SEED,"row_counts":counts,"min_max_years":coverage}
    else:
        result=generate(args.output); result={"status":"generated","seed":result["seed"],"row_counts":result["row_counts"]}
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__": main()

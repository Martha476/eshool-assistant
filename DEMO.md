# Demonstration

> These examples use fixed interpretation outputs and synthetic HTML fixtures.
> They demonstrate application behavior and are not live eSchool results or an
> evaluation of the AI model. Run `python demo.py` with an API key to use live
> interpretation and search.

## 1. Clearly specified request

**Request:** I'm looking for a girls' boarding school in Kampala, preferably around Central Division, charging no more than UGX 1 million per term and currently admitting Senior One students.

```text
[ok] The eSchool search cannot filter on: admission_class. These are checked against each school's visible listing where possible. Found 1 school(s).
Criteria: {'location': 'Kampala', 'county': 'Kampala Central Division', 'max_fees': 1000000, 'gender': 'girls', 'boarding': 'boarding', 'admission_class': 'Senior One', 'admitting_now': True}
Search URL: https://eschool.ug/find-schools/search?location=KAMPALA&county=KAMPALA+CENTRAL+DIVISION&min_fees=&max_fees=1000000&gender=girls&accomadation=Boarding&admission_status=open

1. Example Girls Boarding School  (https://eschool.ug/find-schools/example-girls-boarding)
   Location: Kampala Central Division
   Gender: Girls
   Accommodation: Boarding
   Fees: UGX 900,000
   Admission status: Admitting Senior One
   + located in Kampala
   + in Kampala Central Division
   + Girls school
   + fees UGX 900,000 are within UGX 1,000,000
   + Boarding
   + admission status: Admitting Senior One
   + listing mentions Senior One
```

## 2. Missing / ambiguous information

**Request:** I want a good school for my child.

```text
[needs_clarification] Which area are you looking in, which class is your child joining, and what is your budget per term?
Criteria: (none specified)
```

No eSchool request is made until the parent provides a usable search criterion.

## 3. No suitable results

**Request:** A mixed school in Kampala charging no more than UGX 50,000 per term.

```text
[no_results] No schools matched these criteria. Try widening the fee range, removing the area/division, or searching a nearby location.
Criteria: {'location': 'Kampala', 'max_fees': 50000, 'gender': 'mixed'}
Search URL: https://eschool.ug/find-schools/search?location=KAMPALA&county=&min_fees=&max_fees=50000&gender=mixed
```

The fixture listings have no fees within that limit, so none is shown as a match.

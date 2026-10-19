# Competency questions

The questions this knowledge graph must answer, written before the ontology
(Session 3, slide 40). Every class and property in ontology.ttl answers at least
one of them, recorded on it as pub:answersCQ; a term with no question is deleted.
Asked by LU's research office (R), a researcher or dean (D), or this project (P).

| # | Asked by | Competency question | Classes and properties it needs |
|---|---|---|---|
| CQ1 | R | How many papers did LU publish each year from 2022 to 2025, of each type, and how many are open access? | Work and its 20 types; publicationYear, isOpenAccess |
| CQ2 | D | Which LU researchers publish the most, and how often are they first, last or corresponding author? | Authorship, Author; hasAuthorship, author, affiliation, authorOrder, authorPosition, isCorresponding, name |
| CQ3 | R | With which countries and institutions does LU co-author most, and what kind of institutions are they? | Institution; affiliation, countryCode, institutionType, name |
| CQ4 | R | Where does LU publish (journals, conferences, repositories), and with which publishers? | Venue; publishedIn, venueType, publisher, name |
| CQ5 | R | In which research fields and domains does LU publish, and how does that change by year? | Topic; hasTopic, subfield, field, domain, publicationYear |
| CQ6 | D | Which LU papers cite other LU papers? | cites; across the sources, owl:sameAs (graph/links) |
| CQ7 | R | In which languages does LU publish? | language |
| CQ8 | R | Which LU papers have been retracted? | isRetracted; updates and Retraction (Crossref's notices) |
| CQ9 | P | Which authorships name a person OpenAlex could not identify, and which author records share an ORCID? | nameAsListed, author, orcid; owl:sameAs (graph/links, graph/matches) |
| CQ10 | P | For a paper with a DOI, does a second source (Crossref) agree on its title, date and venue? | doi, title, publicationYear, publicationDate, issnL, venueName, issn |

CQ1 to CQ8 were answered on the OpenAlex graph in Session 3. Since Session 5,
with Crossref and the links: CQ10 compares the two sources, CQ9 follows the
links step by step, and CQ6 and CQ8 have a second query for both sources
(ontology/cq/*_sources.rq). owl:sameAs is OWL's own word, not one of ours.

## Every term of the graph has a question

| Term | CQ | Term | CQ | Term | CQ |
|---|---|---|---|---|---|
| title | 10 | hasTopic | 5 | orcid | 9 |
| doi | 10 | hasAuthorship | 2, 3 | countryCode | 3 |
| language | 7 | authorOrder | 2 | institutionType | 3 |
| publicationYear | 1, 5 | authorPosition | 2 | issnL | 10 |
| publicationDate | 10 | nameAsListed | 9 | venueType | 4 |
| isOpenAccess | 1 | isCorresponding | 2 | publisher | 4 |
| isRetracted | 8 | author | 2, 9 | subfield, field, domain | 5 |
| publishedIn | 4 | affiliation | 2, 3 | cites | 6 |
| name | 2, 3, 4 | updates | 8 | venueName, issn | 10 |
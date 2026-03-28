DROP PROPERTY GRAPH professional_network;

DROP TABLE has_skill;
DROP TABLE knows;
DROP TABLE works_at;
DROP TABLE project_requests;
DROP TABLE skills;
DROP TABLE companies;
DROP TABLE people;

-------------------------------------------------------
-- NODE TABLES
-------------------------------------------------------

CREATE TABLE people (
    person_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name   VARCHAR2(100) NOT NULL,
    city        VARCHAR2(50),
    role        VARCHAR2(100)
);

CREATE TABLE companies (
    company_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_name VARCHAR2(100) NOT NULL,
    sector       VARCHAR2(50)
);

CREATE TABLE skills (
    skill_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    skill_name VARCHAR2(100) NOT NULL,
    category   VARCHAR2(50)
);

-------------------------------------------------------
-- EDGE TABLES
-------------------------------------------------------

-- A person WORKS AT a company
CREATE TABLE works_at (
    edge_id     NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    person_id   NUMBER NOT NULL REFERENCES people(person_id),
    company_id  NUMBER NOT NULL REFERENCES companies(company_id),
    since_year  NUMBER
);

-- A person KNOWS another person
CREATE TABLE knows (
    edge_id      NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    person_id_1  NUMBER NOT NULL REFERENCES people(person_id),
    person_id_2  NUMBER NOT NULL REFERENCES people(person_id),
    relationship VARCHAR2(50)  -- 'colleague', 'friend', 'mentor'
);

-- A person HAS a skill
CREATE TABLE has_skill (
    edge_id    NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    person_id  NUMBER NOT NULL REFERENCES people(person_id),
    skill_id   NUMBER NOT NULL REFERENCES skills(skill_id),
    job_level  VARCHAR2(20)   -- 'beginner', 'intermediate', 'expert'
);

-------------------------------------------------------
-- NODES
-------------------------------------------------------

INSERT INTO people (full_name, city, role) VALUES ('Marco Rossi',    'Rome',    'Cloud Architect');
INSERT INTO people (full_name, city, role) VALUES ('Laura Bianchi',  'Milan',   'Data Engineer');
INSERT INTO people (full_name, city, role) VALUES ('Paolo Verdi',    'Naples',  'DBA');
INSERT INTO people (full_name, city, role) VALUES ('Sara Neri',      'Turin',   'ML Engineer');
INSERT INTO people (full_name, city, role) VALUES ('Luca Galli',     'Rome',    'DevOps Engineer');

INSERT INTO companies (company_name, sector) VALUES ('TechCorp',     'IT');
INSERT INTO companies (company_name, sector) VALUES ('DataWave',     'Consulting');
INSERT INTO companies (company_name, sector) VALUES ('CloudNine',    'Cloud Services');

INSERT INTO skills (skill_name, category) VALUES ('Oracle DB',       'Database');
INSERT INTO skills (skill_name, category) VALUES ('Kubernetes',      'Infrastructure');
INSERT INTO skills (skill_name, category) VALUES ('Python',          'Language');
INSERT INTO skills (skill_name, category) VALUES ('Machine Learning','AI');

COMMIT;

-------------------------------------------------------
-- EDGES: who works where
-------------------------------------------------------

INSERT INTO works_at (person_id, company_id, since_year) VALUES (1, 1, 2019);  -- Marco -> TechCorp
INSERT INTO works_at (person_id, company_id, since_year) VALUES (2, 2, 2020);  -- Laura -> DataWave
INSERT INTO works_at (person_id, company_id, since_year) VALUES (3, 1, 2017);  -- Paolo -> TechCorp
INSERT INTO works_at (person_id, company_id, since_year) VALUES (4, 3, 2021);  -- Sara  -> CloudNine
INSERT INTO works_at (person_id, company_id, since_year) VALUES (5, 1, 2022);  -- Luca  -> TechCorp

-------------------------------------------------------
-- EDGES: who knows whom
-------------------------------------------------------

INSERT INTO knows (person_id_1, person_id_2, relationship) VALUES (1, 2, 'friend');
INSERT INTO knows (person_id_1, person_id_2, relationship) VALUES (1, 3, 'colleague');
INSERT INTO knows (person_id_1, person_id_2, relationship) VALUES (2, 4, 'colleague');
INSERT INTO knows (person_id_1, person_id_2, relationship) VALUES (3, 5, 'mentor');
INSERT INTO knows (person_id_1, person_id_2, relationship) VALUES (4, 5, 'friend');

-------------------------------------------------------
-- EDGES: who has which skill
-------------------------------------------------------

INSERT INTO has_skill (person_id, skill_id, job_level) VALUES (1, 2, 'expert');
INSERT INTO has_skill (person_id, skill_id, job_level) VALUES (1, 1, 'intermediate');
INSERT INTO has_skill (person_id, skill_id, job_level) VALUES (2, 3, 'expert');
INSERT INTO has_skill (person_id, skill_id, job_level) VALUES (2, 4, 'intermediate');
INSERT INTO has_skill (person_id, skill_id, job_level) VALUES (3, 1, 'expert');
INSERT INTO has_skill (person_id, skill_id, job_level) VALUES (4, 4, 'expert');
INSERT INTO has_skill (person_id, skill_id, job_level) VALUES (4, 3, 'expert');
INSERT INTO has_skill (person_id, skill_id, job_level) VALUES (5, 2, 'intermediate');

COMMIT;

-------------------------------------------------------
-- PROPERTY GRAPH
-------------------------------------------------------

CREATE PROPERTY GRAPH professional_network

  VERTEX TABLES (
    people
      KEY (person_id)
      LABEL Person
      PROPERTIES (full_name, city, role),

    companies
      KEY (company_id)
      LABEL Company
      PROPERTIES (company_name, sector),

    skills
      KEY (skill_id)
      LABEL Skill
      PROPERTIES (skill_name, category)
  )

  EDGE TABLES (
    works_at
      KEY (edge_id)
      SOURCE KEY (person_id) REFERENCES people (person_id)
      DESTINATION KEY (company_id) REFERENCES companies (company_id)
      LABEL WORKS_AT
      PROPERTIES (since_year),

    knows
      KEY (edge_id)
      SOURCE KEY (person_id_1) REFERENCES people (person_id)
      DESTINATION KEY (person_id_2) REFERENCES people (person_id)
      LABEL KNOWS
      PROPERTIES (relationship),

    has_skill
      KEY (edge_id)
      SOURCE KEY (person_id) REFERENCES people (person_id)
      DESTINATION KEY (skill_id) REFERENCES skills (skill_id)
      LABEL HAS_SKILL
      PROPERTIES (job_level)
  );

-------------------------------------------------------
-- QUERY 1: where people work
-------------------------------------------------------

SELECT *
FROM GRAPH_TABLE (
    professional_network
    MATCH (p IS Person) -[w IS WORKS_AT]-> (c IS Company)
    COLUMNS (
        VERTEX_ID(p)   AS p_id,
        VERTEX_ID(c)   AS c_id,
        EDGE_ID(w)     AS w_id,
        p.full_name    AS person_name,
        c.company_name AS company,
        w.since_year   AS since
    )
)
ORDER BY since;

-------------------------------------------------------
-- QUERY 2: who knows whom
-------------------------------------------------------

SELECT *
FROM GRAPH_TABLE (
    professional_network
    MATCH (a IS Person) -[k IS KNOWS]-> (b IS Person)
    COLUMNS (
        VERTEX_ID(a)   AS a_id,
        VERTEX_ID(b)   AS b_id,
        EDGE_ID(k)     AS k_id,
        a.full_name    AS person_1,
        b.full_name    AS person_2,
        k.relationship AS relationship_type
    )
)
ORDER BY relationship_type;

-------------------------------------------------------
-- QUERY 3: person -> company + skill
-------------------------------------------------------

SELECT *
FROM GRAPH_TABLE (
    professional_network
    MATCH 
        (p IS Person) -[w IS WORKS_AT]->  (c IS Company),
        (p)           -[h IS HAS_SKILL]-> (s IS Skill)
    COLUMNS (
        VERTEX_ID(p)   AS p_id,
        VERTEX_ID(c)   AS c_id,
        VERTEX_ID(s)   AS s_id,
        EDGE_ID(w)     AS w_id,
        EDGE_ID(h)     AS h_id,
        p.full_name    AS person_name,
        p.role         AS job_role,
        c.company_name AS company,
        s.skill_name   AS skill,
        h.job_level    AS skill_level
    )
)
ORDER BY person_name, skill;

-------------------------------------------------------
-- QUERY 4: friends of friends (2-hop path)
-------------------------------------------------------

SELECT *
FROM GRAPH_TABLE (
    professional_network
    MATCH (a IS Person) -[k1 IS KNOWS]-> (b IS Person) -[k2 IS KNOWS]-> (c IS Person)
    WHERE VERTEX_ID(a) <> VERTEX_ID(c)
    COLUMNS (
        VERTEX_ID(a)   AS a_id,
        VERTEX_ID(b)   AS b_id,
        VERTEX_ID(c)   AS c_id,
        EDGE_ID(k1)    AS k1_id,
        EDGE_ID(k2)    AS k2_id,
        a.full_name    AS person_name,
        b.full_name    AS through,
        c.full_name    AS friend_of_friend
    )
)
ORDER BY person_name;

-------------------------------------------------------
-- PROJECT REQUESTS TABLE
-------------------------------------------------------

CREATE TABLE project_requests (
    request_id     NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_name   VARCHAR2(100),
    required_skill VARCHAR2(100),
    min_level      VARCHAR2(20)
);

INSERT INTO project_requests (project_name, required_skill, min_level) 
    VALUES ('Cloud Migration', 'Kubernetes', 'expert');
INSERT INTO project_requests (project_name, required_skill, min_level) 
    VALUES ('Data Pipeline', 'Python', 'expert');
COMMIT;

-------------------------------------------------------
-- QUERY 5: relational-graph fusion with CROSS JOIN LATERAL
-------------------------------------------------------

SELECT 
    pr.project_name,
    gt.p_id,
    gt.s_id,
    gt.c_id,
    gt.h_id,
    gt.w_id,
    gt.person_name,
    gt.company,
    gt.skill,
    gt.skill_level
FROM 
    project_requests pr
    CROSS JOIN LATERAL (
        SELECT *
        FROM GRAPH_TABLE (
            professional_network
            MATCH 
                (p IS Person) -[h IS HAS_SKILL]-> (s IS Skill),
                (p)           -[w IS WORKS_AT]->  (c IS Company)
            COLUMNS (
                VERTEX_ID(p)   AS p_id,
                VERTEX_ID(s)   AS s_id,
                VERTEX_ID(c)   AS c_id,
                EDGE_ID(h)     AS h_id,
                EDGE_ID(w)     AS w_id,
                p.full_name    AS person_name,
                s.skill_name   AS skill,
                h.job_level    AS skill_level,
                c.company_name AS company
            )
        )
        WHERE UPPER(skill) = UPPER(pr.required_skill)
          AND skill_level = pr.min_level
    ) gt
ORDER BY pr.project_name, gt.person_name;
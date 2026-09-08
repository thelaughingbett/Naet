# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Static UNESCO ISCED field-of-study reference table. Split out of
academics.py because it's a reference dataset, not model logic — both
Programme and Course reference it as a `choices=` list, and having it
live at the top of a model file that also defines seven classes just
pushed the actual model code 100+ lines down the file for no benefit.
"""

UNESCO_ISCED_FIELDS = [
    # 00 Generic Programmes and Qualifications
    ('0011', 'Basic programmes and qualifications'),
    ('0021', 'Literacy and numeracy'),
    ('0031', 'Personal skills and development'),
    ('0099', 'Generic programmes and qualifications not elsewhere classified'),

    # 01 Education
    ('0111', 'Education science'),
    ('0112', 'Training for pre-school teachers'),
    ('0113', 'Teacher training without subject specialisation'),
    ('0114', 'Teacher training with subject specialisation'),
    ('0188', 'Inter-disciplinary programmes involving education'),

    # 02 Arts and Humanities
    ('0211', 'Audio-visual techniques and media production'),
    ('0212', 'Fashion, interior and industrial design'),
    ('0213', 'Fine arts'),
    ('0214', 'Handicrafts'),
    ('0215', 'Music and performing arts'),
    ('0221', 'Religion and theology'),
    ('0222', 'History and archaeology'),
    ('0223', 'Philosophy and ethics'),
    ('0231', 'Language acquisition'),
    ('0232', 'Literature and linguistics'),
    ('0288', 'Inter-disciplinary programmes involving arts and humanities'),

    # 03 Social Sciences, Journalism and Information
    ('0311', 'Economics'),
    ('0312', 'Political sciences and civics'),
    ('0313', 'Psychology'),
    ('0314', 'Sociology and cultural studies'),
    ('0321', 'Journalism and reporting'),
    ('0322', 'Library, information and archival studies'),
    ('0388', 'Inter-disciplinary programmes involving social sciences/journalism'),

    # 04 Business, Administration and Law
    ('0411', 'Accounting and taxation'),
    ('0412', 'Finance, banking and insurance'),
    ('0413', 'Management and administration'),
    ('0414', 'Marketing and advertising'),
    ('0415', 'Secretarial and office work'),
    ('0416', 'Wholesale and retail sales'),
    ('0417', 'Work skills'),
    ('0421', 'Law'),
    ('0488', 'Inter-disciplinary programmes involving business/admin/law'),

    # 05 Natural Sciences, Mathematics and Statistics
    ('0511', 'Biology'),
    ('0512', 'Biochemistry'),
    ('0521', 'Environmental sciences'),
    ('0522', 'Natural environments and wildlife'),
    ('0531', 'Chemistry'),
    ('0532', 'Earth sciences'),
    ('0533', 'Physics'),
    ('0541', 'Mathematics'),
    ('0542', 'Statistics'),
    ('0588', 'Inter-disciplinary programmes involving natural sciences/maths'),

    # 06 Information and Communication Technologies (ICTs)
    ('0611', 'Computer use (Basic IT/Applications)'),
    ('0612', 'Database and network design and administration'),
    ('0613', 'Software and applications development and analysis (Computer Science)'),
    ('0688', 'Inter-disciplinary programmes involving ICTs'),

    # 07 Engineering, Manufacturing and Construction
    ('0711', 'Chemical engineering and processes'),
    ('0712', 'Environmental protection technology'),
    ('0713', 'Electricity and energy'),
    ('0714', 'Electronics and automation (Mechatronics/Hardware Engineering)'),
    ('0715', 'Mechanics and metal trades'),
    ('0716', 'Motor vehicles, ships and aircraft (Aeronautical/Automotive)'),
    ('0721', 'Food processing'),
    ('0722', 'Materials (glass, paper, plastic and wood)'),
    ('0723', 'Textiles (clothes, footwear and leather)'),
    ('0724', 'Mining and extraction'),
    ('0731', 'Architecture and town planning'),
    ('0732', 'Building and civil engineering'),
    ('0788', 'Inter-disciplinary programmes involving engineering/construction'),

    # 08 Agriculture, Forestry, Fisheries and Veterinary
    ('0811', 'Crop and livestock production'),
    ('0812', 'Horticulture'),
    ('0821', 'Forestry'),
    ('0831', 'Fisheries'),
    ('0841', 'Veterinary'),
    ('0888', 'Inter-disciplinary programmes involving agriculture/veterinary'),

    # 09 Health and Welfare
    ('0911', 'Dental studies'),
    ('0912', 'Medicine (Clinical Medicine/Surgery/MBChB)'),
    ('0913', 'Nursing and midwifery'),
    ('0914', 'Medical diagnostic and treatment technology (Radiology/Lab Tech)'),
    ('0915', 'Therapy and rehabilitation (Physiotherapy)'),
    ('0916', 'Pharmacy'),
    ('0917', 'Traditional and complementary medicine and therapy'),
    ('0921', 'Care of elderly and of disabled adults'),
    ('0922', 'Child care and youth services'),
    ('0923', 'Social work and counselling'),
    ('0988', 'Inter-disciplinary programmes involving health and welfare'),

    # 10 Services
    ('1011', 'Domestic services'),
    ('1012', 'Hair and beauty services'),
    ('1013', 'Hotel, restaurants and catering'),
    ('1014', 'Sports'),
    ('1015', 'Travel, tourism and leisure'),
    ('1021', 'Community sanitation'),
    ('1022', 'Occupational health and safety'),
    ('1031', 'Military science and defence'),
    ('1032', 'Protection of persons and property (Security Management/Police)'),
    ('1041', 'Transport services (Logistics/Aviation operations)'),
    ('1088', 'Inter-disciplinary programmes involving services'),
]

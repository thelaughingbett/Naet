 # Delete all migration files (keep __init__.py)                                                                                    
>> del base\migrations\0*.py
>> 
>> # Recreate them
>> python manage.py makemigrations base
>> python manage.py migrate
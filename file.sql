-- Drop the existing trigger function if it exists
DROP FUNCTION IF EXISTS update_entry_and_edit_fields;

-- Create the trigger function for updating entry and edit fields
CREATE OR REPLACE FUNCTION update_entry_and_edit_fields()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.entry_person := current_user;
        NEW.entry_date := CURRENT_DATE;
    ELSIF TG_OP = 'UPDATE' THEN
        NEW.edit_person := current_user;
        NEW.edit_date := CURRENT_DATE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop the existing triggers if they exist
DROP TRIGGER IF EXISTS update_university_entry_and_edit_fields ON myapp_university;
DROP TRIGGER IF EXISTS update_institute_entry_and_edit_fields ON myapp_institute;
DROP TRIGGER IF EXISTS update_program_entry_and_edit_fields ON myapp_program;
DROP TRIGGER IF EXISTS update_branch_entry_and_edit_fields ON myapp_branch;

-- Create the triggers for updating entry and edit fields
CREATE TRIGGER update_university_entry_and_edit_fields
BEFORE INSERT OR UPDATE ON myapp_university
FOR EACH ROW EXECUTE FUNCTION update_entry_and_edit_fields();

CREATE TRIGGER update_institute_entry_and_edit_fields
BEFORE INSERT OR UPDATE ON myapp_institute
FOR EACH ROW EXECUTE FUNCTION update_entry_and_edit_fields();

CREATE TRIGGER update_program_entry_and_edit_fields
BEFORE INSERT OR UPDATE ON myapp_program
FOR EACH ROW EXECUTE FUNCTION update_entry_and_edit_fields();

CREATE TRIGGER update_branch_entry_and_edit_fields
BEFORE INSERT OR UPDATE ON myapp_branch
FOR EACH ROW EXECUTE FUNCTION update_entry_and_edit_fields();

import pandas as pd
import spacy

# Load the spaCy model for Named Entity Recognition
nlp = spacy.load("en_core_web_sm")

# Function to extract names from sentences
def extract_names(sentence):
    doc = nlp(sentence)
    names = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    return ", ".join(names)

# Function to preprocess the CSV file
def preprocess_csv(file_path):
    # Load the CSV file into a DataFrame
    df = pd.read_csv(file_path, encoding='ISO-8859-1')

    # Apply the extract_names function to the relevant columns
    for column in ["CEO", "CTO", "IT_Manager"]:
        if column in df.columns:
            df[column] = df[column].astype(str).apply(extract_names)

    # Save the updated DataFrame back to the CSV file
    df.to_csv(file_path, index=False)

    print("Names have been extracted and updated in the CSV file.")

# Async function to process the NLP
async def process_nlp(file_path):
    preprocess_csv(file_path)

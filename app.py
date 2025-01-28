import streamlit as st
import pandas as pd
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
import matplotlib.pyplot as plt
from PIL import Image  # Import PIL for image handling

# MongoDB connection (Update with your actual connection string)
client = MongoClient("mongodb://localhost:27017/")
db = client["social_media"]  # The name of your MongoDB database

# Function to retrieve data
def load_data(collection_name):
    collection = db[collection_name]
    data = pd.DataFrame(list(collection.find()))
    if not data.empty:
        data['_id'] = data['_id'].astype(str)  # Convert ObjectId to string for display
    return data

# Function to highlight the modified row
def highlight_row(data, row_id=None):
    styles = pd.DataFrame('', index=data.index, columns=data.columns)
    if row_id is not None:
        styles.loc[data['_id'] == row_id, :] = 'background-color: yellow'
    return styles

# Function to add custom CSS for buttons and centering images
def add_custom_css():
    st.markdown("""
    <style>
    .stImage {
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
    .stButton>button {
        width: 100%;
    }
    .back-button {
        position: absolute;
        top: 10px;
        left: 10px;
        background-color: transparent;
        border: none;
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)

# Back button logic
def back_button(previous_screen):
    if st.button("⬅️", key="back-button"):
        st.session_state['current_screen'] = previous_screen
        st.experimental_rerun()

# Screen 1: Welcome Screen
def welcome_screen():
    add_custom_css()
    st.title("X Data Management App")

    # Load the logo image from a local file
    logo_image = Image.open("logo.png")  # Ensure this file is in the same directory
    st.image(logo_image, width=300)  # Display the image without caption

    if 'dataset_list' not in st.session_state or st.session_state['dataset_list'] is None:
        st.session_state['dataset_list'] = db.list_collection_names()

    dataset_names = st.session_state['dataset_list']
    
    # Option 1: Select an existing collection
    st.subheader("Select an existing dataset to manage:")
    selected_dataset = st.selectbox("Choose a dataset:", dataset_names)

    if st.button("🚀 Proceed"):
        st.session_state.selected_dataset = selected_dataset
        st.session_state['current_screen'] = 'dataset_selection_screen'
        st.experimental_rerun()

    # Option 2: Create a new collection by uploading a CSV file
    st.subheader("Upload a CSV file to create a new collection:")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file:
        new_collection_name = st.text_input("Enter the name for the new collection:")
        if st.button("Create Collection"):
            if new_collection_name:
                csv_data = pd.read_csv(uploaded_file)
                records = csv_data.to_dict(orient='records')
                db[new_collection_name].insert_many(records)
                st.session_state['dataset_list'] = None  # Reset dataset list
                st.success(f"New collection '{new_collection_name}' created successfully!")
            else:
                st.error("Please enter a valid collection name.")

    # Option 3: Delete an existing collection
    st.subheader("Delete an existing dataset:")
    collection_to_delete = st.selectbox("Select a collection to delete:", dataset_names)

    if st.button("❌ Delete Collection"):
        if collection_to_delete:
            db[collection_to_delete].drop()
            st.session_state['dataset_list'] = None  # Reset dataset list
            st.error(f"Collection '{collection_to_delete}' deleted successfully!")

# Screen 2: Dataset Selection
def dataset_selection_screen():
    back_button('welcome_screen')  # Back button to return to the welcome screen
    add_custom_css()

    dataset = st.session_state.selected_dataset
    st.title(f"Managing {dataset}")
    
    data = load_data(dataset)
    st.subheader(f"Number of Records: {len(data)}")

    if data.empty:
        st.write("No data available.")
        return

    modified_row_id = st.session_state.get('modified_row_id', None)
    
    if modified_row_id:
        st.dataframe(data.style.apply(highlight_row, row_id=modified_row_id, axis=None))
    else:
        st.dataframe(data)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("➕ Add Data"):
            st.session_state['current_screen'] = 'add_data_screen'
            st.experimental_rerun()

    with col2:
        if st.button("✏️ Update Data"):
            st.session_state['current_screen'] = 'update_data_screen'
            st.experimental_rerun()

    with col3:
        if st.button("🗑️ Delete Data"):
            st.session_state['current_screen'] = 'delete_data_screen'
            st.experimental_rerun()

    with col4:
        if st.button("📊 Analyze Data"):
            st.session_state['current_screen'] = 'analyze_data_screen'
            st.experimental_rerun()

# Screen 3: Add Data
def add_data_screen():
    back_button('dataset_selection_screen')  # Back button to return to dataset selection
    add_custom_css()

    dataset = st.session_state.selected_dataset
    st.title(f"Add Data to {dataset}")

    with st.form("add_form"):
        new_data = {}
        columns = load_data(dataset).columns
        for column in columns:
            if column != "_id":
                new_data[column] = st.text_input(f"Enter {column}:")
        
        if st.form_submit_button("Submit"):
            inserted_id = db[dataset].insert_one(new_data).inserted_id
            st.session_state['modified_row_id'] = str(inserted_id)
            st.success("Data added successfully!")  # Green popup message
            st.session_state['current_screen'] = 'dataset_selection_screen'  # Redirect to dataset selection
            st.experimental_rerun()

# Screen 4: Update Data
def update_data_screen():
    back_button('dataset_selection_screen')  # Back button to return to dataset selection
    add_custom_css()

    dataset = st.session_state.selected_dataset
    st.title(f"Update Data in {dataset}")

    data = load_data(dataset)
    if data.empty:
        st.write("No data available to update.")
        return

    search_term = st.text_input("Search:", "")
    if search_term:
        data = data[data.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)]

    if not data.empty:
        selected_id = st.selectbox("Select Data ID to Update:", data['_id'])
        if selected_id:
            try:
                selected_object_id = ObjectId(selected_id)
                selected_data = data[data['_id'] == selected_id].iloc[0]
                
                with st.form("update_form"):
                    updated_data = {}
                    for column in selected_data.index:
                        updated_data[column] = st.text_input(f"Update {column}:", selected_data[column])
                    
                    if '_id' in updated_data:
                        del updated_data['_id']

                    if st.form_submit_button("Submit"):
                        db[dataset].update_one({"_id": selected_object_id}, {"$set": updated_data})
                        st.session_state['modified_row_id'] = str(selected_id)
                        st.info("Data updated successfully!")  # Blue popup message
                        st.session_state['current_screen'] = 'dataset_selection_screen'  # Redirect to dataset selection
                        st.experimental_rerun()

            except InvalidId:
                st.error(f"'{selected_id}' is not a valid ObjectId.")

# Screen 5: Delete Data
def delete_data_screen():
    back_button('dataset_selection_screen')  # Back button to return to dataset selection
    add_custom_css()

    dataset = st.session_state.selected_dataset
    st.title(f"Delete Data from {dataset}")

    data = load_data(dataset)
    if data.empty:
        st.write("No data available to delete.")
        return

    search_term = st.text_input("Search:", "")
    if search_term:
        data = data[data.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)]

    if not data.empty:
        selected_id = st.selectbox("Select Data ID to Delete:", data['_id'])
        if selected_id:
            if st.button("🗑️ Delete"):
                db[dataset].delete_one({"_id": ObjectId(selected_id)})
                st.session_state['modified_row_id'] = str(selected_id)
                st.error("Data deleted successfully!")  # Red popup message
                st.session_state['current_screen'] = 'dataset_selection_screen'  # Redirect to dataset selection
                st.experimental_rerun()

# Screen 6: Analyze Data
def analyze_data_screen():
    back_button('dataset_selection_screen')  # Back button to return to dataset selection
    add_custom_css()

    dataset = st.session_state.selected_dataset
    st.title(f"Analyze Data in {dataset}")

    data = load_data(dataset)
    if data.empty:
        st.write("No data available for analysis.")
        return

    numerical_cols = data.select_dtypes(include='number').columns.tolist()
    if numerical_cols:
        selected_col = st.selectbox("Select a numerical column for analysis:", numerical_cols)
        st.subheader(f"Analysis of {selected_col}")

        plt.figure(figsize=(10, 5))
        plt.hist(data[selected_col], bins=20, alpha=0.7)
        plt.title(f"Histogram of {selected_col}")
        plt.xlabel(selected_col)
        plt.ylabel("Frequency")
        st.pyplot(plt)

    else:
        st.write("No numerical columns available for analysis.")

# Main function to control the app flow
def main():
    if 'current_screen' not in st.session_state:
        st.session_state['current_screen'] = 'welcome_screen'

    screen_mapping = {
        'welcome_screen': welcome_screen,
        'dataset_selection_screen': dataset_selection_screen,
        'add_data_screen': add_data_screen,
        'update_data_screen': update_data_screen,
        'delete_data_screen': delete_data_screen,
        'analyze_data_screen': analyze_data_screen,
    }

    current_screen = st.session_state['current_screen']
    screen_mapping[current_screen]()

if __name__ == "__main__":
    main()

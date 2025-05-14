from langchain_community.document_loaders import PyPDFLoader


class PDFLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.loader = PyPDFLoader(file_path)

    def load_document(self) -> str:
        ret_str = ""
        for page in self.loader.load():
            ret_str += page.page_content

        return "".join([page.page_content for page in self.loader.load()])

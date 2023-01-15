import os
import requests
import flet as ft
from time import sleep
from typing import Any, Dict, List, Tuple, Optional
from flet import (
    Text, TextField, TextThemeStyle, 
    Markdown, FloatingActionButton, icons,
    Page, Column, Row, 
)

API_ENDPOINT = os.getenv("API_ENDPOINT", "http://localhost:8000")
DOC_REQUEST = "query"
TOP_K_RETRIEVER = 5

def main(page: Page):
    page.title = "Search or Ask Questions"
    page.horizontal_alignment = "center"
    page.scroll = "adaptive"

    def query(
        query, filters={}, top_k_reader=5, top_k_retriever=TOP_K_RETRIEVER
    ) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        """
        Send a query to the REST API and parse the answer.
        Returns both a ready-to-use representation of the results and the raw JSON.
        """

        url = f"{API_ENDPOINT}/{DOC_REQUEST}"
        params = {
            "filters": filters, 
            "Retriever": {"top_k": top_k_retriever}, 
            "Reader": {"top_k": top_k_reader}
        }
        req = {"query": query, "params": params}
        response_raw = requests.post(url, json=req)

        if response_raw.status_code >= 400 and response_raw.status_code != 503:
            raise Exception(f"{vars(response_raw)}")

        response = response_raw.json()
        if "errors" in response:
            raise Exception(", ".join(response["errors"]))

        # Format response
        results = []
        answers = response["answers"]
        for answer in answers:
            if answer.get("answer", None):
                results.append(
                    {
                        "context": "..." + answer["context"] + "...",
                        "answer": answer.get("answer", None),
                        "source": answer["meta"]["name"],
                        "relevance": round(answer["score"] * 100, 2),
                        "document": [doc for doc in response["documents"] 
                                    if doc["id"] == answer["document_id"]][0],
                        "offset_start_in_doc": answer["offsets_in_document"][0]["start"],
                        "_raw": answer,
                    }
                )
            else:
                results.append(
                    {
                        "context": None,
                        "answer": None,
                        "document": None,
                        "relevance": round(answer["score"] * 100, 2),
                        "_raw": answer,
                    }
                )
        return results, response

    def search_triggered(e):
        search_results.value = "Looking for answers ..."
        search_results.visible = True
        progress_ring.visible = True
        answers_list.controls = []
        
        page.update()
        query_string = search_query.value
        results, response = {}, {}
        if search_query.value:
            try: 
                results, response = query(query_string)
                display_results(results)
                page.update()
            except:
                sleep(1)
                progress_ring.visible = False
                # ERROR_OUTLINE
                search_results.value = 'ERROR: The question-answering API is offline'
                page.update()
        else:
            search_results.value = 'Type your query in the text box above to run it'
            answers_list.controls.append(
                Markdown("""Alternatively, you can click **Set example query** button above 
                         to have the query text box populated with a default example question.""")
            )
            progress_ring.visible = False
            
            page.update()
            
            
        print('results: ', len(results))
        print('response: ', len(response))
        

    def reset_results(e):
        if search_results.value != "Search results will be dislayed here":
            search_results.value = "Search results will be dislayed here"        
        page.update()
        
    def get_backlink(result) -> Tuple[Optional[str], Optional[str]]:
        if result.get("document", None):
            doc = result["document"]
            if isinstance(doc, dict):
                if doc.get("meta", None):
                    if isinstance(doc["meta"], dict):
                        if doc["meta"].get("url", None) and doc["meta"].get("title", None):
                            return doc["meta"]["url"], doc["meta"]["title"]
        return None, None   
        
    def display_results(results):
        search_results.value = ''
        progress_ring.visible = False
        answers_list.controls.append(Markdown(f"### Your query was: '{search_query.value}'"))
        answers_list.controls.append(Markdown(f"## These are the top {TOP_K_RETRIEVER} results found: "))
        page.update()

        for count, result in enumerate(results):
            if result["answer"]:
                answer, context = result["answer"], result["context"]
                start_idx = context.find(answer)
                end_idx = start_idx + len(answer)
                span_answer = f" **{answer}** "
                par = context[:start_idx] + span_answer + context[end_idx:]
                answers_list.controls.append(Markdown(par))
                page.update()        
                
                source = ""
                url, title = get_backlink(result)
                if url and title:
                    source = f"[{result['document']['meta']['title']}]({result['document']['meta']['url']})"
                else:
                    source = f"{result['source']}"
                
                answers_list.controls.append(Markdown(
                    f"**Confidence:** {result['relevance']} -  **Source:** {source}"
                ))
                page.update()
            else:
                answers_list.controls.append(Markdown(
                    "Unsure whether this document contains an answer to your question ..."
                ))
                answers_list.controls.append(Markdown(f"**Confidence:** {result['relevance']}"))
                page.update()
                
            answers_list.controls.append(Markdown("___"))
            page.update()
            
        search_query.value = ''
        search_results.visible = False
        page.update()
    
        
    search_query = TextField(
        hint_text="What is your query?",
        on_submit=search_triggered,
        on_change=reset_results,
        expand=True)

    search_button = FloatingActionButton(
        "Run the query",
        icon=icons.SEARCH, 
        bgcolor=ft.colors.GREEN_200,
        on_click=search_triggered,
        # tooltip='Run query!'
    )

    search_results = Text(
        "Search results will be dislayed here",
        style=TextThemeStyle.TITLE_LARGE,
    )
    
    answers_list = ft.ListView(expand=1, spacing=10, padding=20, auto_scroll=True)
    
    progress_ring = ft.ProgressRing()
    progress_ring.visible = False
    
    SAMPLE_QUERY = 'What is the capital of The Netherlands?'
    def set_sample_query(e):
        search_query.value = SAMPLE_QUERY
        page.update()
        
    example_button = FloatingActionButton(
        content=ft.Row(
            [
                ft.Text("Set example query"),
                ft.Icon(icons.CONTACT_SUPPORT_OUTLINED), 
            ], alignment="center", 
            spacing=5
        ),
        width=190,
        bgcolor=ft.colors.ORANGE_100,
        on_click=set_sample_query,
        tooltip='Click to use an example query'
    )
    
    page.add(
        Column(
            width=600,
            controls=[
                Row([
                    Text(
                        value="Write a query", 
                        style="headlineMedium"
                    )
                ], alignment="center"),
                Row([
                    search_query,
                ]),
                Row([
                    search_button,
                    example_button,
                ], alignment="center"),
                Row([
                    progress_ring,
                    search_results,
                ], alignment="center"),
                Row([
                    answers_list,
                ], alignment="center"),
            ]
        )
    )

ft.app(
    target=main,
    # view=ft.WEB_BROWSER,
    # assets_dir="assets" # page.add(ft.Image(src=f"/images/my-image.png"))
)
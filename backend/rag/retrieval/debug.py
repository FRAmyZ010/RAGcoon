from .service import search_with_details


def run_sample_queries(queries: list[str]) -> None:
    print("\n" + "=" * 50)
    print("Senior Project Document QA System")
    print("=" * 50)

    for query in queries:
        result = search_with_details(query)
        elapsed = result["timing"]["total_seconds"]

        print("RESULT")
        print("=" * 50)
        print(f"Query: {query}\n")

        if not result["results"]:
            print("No results found")
        else:
            print("Documents retrieved successfully")
            for item in result["results"]:
                print(f"Source: {item['payload']['source']}")

        print("\n" + "-" * 50)
        print(f"Time: {elapsed:.3f} seconds")
        print("=" * 50)
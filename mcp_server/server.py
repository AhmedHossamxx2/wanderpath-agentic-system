from fastmcp import FastMCP


# Create the server skeleton
# The name provided here will be declared during the initialize handshake
server = FastMCP("WanderpathTravelAgent")

if __name__ == "__main__":
    # This automatically sets up the stdio transport and begins listening 
    # for the client's initialize request.
    server.run()
from typing import Dict, List, Union

from github.PullRequest import PullRequest as ghPullRequest
from rich.table import Table

from reviews import config
from reviews.datasource import Label, PullRequest
from reviews.layout import render_pull_request_table
from reviews.source_control import GithubAPI


class PullRequestController:
    """retrieve and store pull requests."""

    def __init__(self) -> None:
        self.client = GithubAPI()

    def retrieve_pull_requests(self, org: str, repository: str) -> Union[Table, None]:
        """Renders Terminal UI Dashboard"""

        title = f"{org}/{repository}"
        pull_requests = self.update_pull_requests(org=org, repository=repository)

        if not pull_requests:
            return None

        return render_pull_request_table(
            title=title,
            pull_requests=pull_requests,
            org=org,
            repository=repository,
        )

    def update_pull_requests(self, org: str, repository: str) -> List[PullRequest]:
        """Updates repository models."""

        def _get_reviews(pull_request: ghPullRequest) -> Dict[str, str]:
            """Inner function to retrieve reviews for a pull request"""
            reviews = pull_request.get_reviews()
            res, seen = {}, []
            for review in reviews:
                if review.user.login in seen or review.state == "COMMENTED":
                    continue
                res[review.user.login] = review.state
                seen.append(review.user.login)
            return res

        pull_requests = self.client.get_pull_requests(org=org, repo=repository)
        return [
            PullRequest(
                number=pull_request.number,
                title=pull_request.title,
                created_at=pull_request.created_at,
                updated_at=pull_request.updated_at,
                approved=_get_reviews(pull_request=pull_request).get(
                    config.GITHUB_USER, ""
                ),  # NOQA: R1721
                approved_by_others=any(
                    [
                        True
                        for user, status in _get_reviews(
                            pull_request=pull_request
                        ).items()
                        if user != config.GITHUB_USER and status == "APPROVED"
                    ]
                ),
                labels=[
                    Label(name=label.name)
                    for label in pull_request.get_labels()
                    if label.name
                ],
            )
            for pull_request in pull_requests
        ]

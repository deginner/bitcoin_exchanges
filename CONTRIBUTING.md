# Contributing to this Project
**Here's how you can help.**

## Process
This project follows [the Forking Flow](http://www.dalescott.net/wordpress/?p=1266), a derivative of [the Gitflow model](http://nvie.com/posts/a-successful-git-branching-model/).  We use Pull Requests to develop conversations around ideas, and turn ideas into actions.

**Some PR Basics**
- Anyone can submit a Pull Request with changes they'd like to see made.
- Pull Requests should attempt to solve a single [1], clearly defined problem [2].
- Everyone should submit Pull Requests early (within the first few commits), so everyone on the team is aware of the direction you're taking.
- Authors are responsible for explicitly tagging anyone who might be impacted by the pull request and get the recipient's sign-off [3].
- The Pull Request should serve as the authority on the status of a change, so everyone on the team is aware of the plan of action.
- Relevant domain authority _must_ sign-off on a pull request before it is merged [4].
- Anyone _except_ the author can merge a pull request once all sign-offs are complete.

[1]: if there are multiple problems you're solving, it is recommended that you create a branch for each.  For example, if you are implementing a small change and realize you want to refactor an entire function, you might want to implement the refactor as your first branch (and pull request), then create a new branch (and pull request) from the refactor to implement your new _feature_.  This helps resolve merge conflicts and separates out the logical components of the decision-making process.

[2]: include a description of the problem that is being resolved in the description field, or a reference to the issue number where the problem is reported.  Examples include; "Follow Button doesn't Reflect State of Follow" or "Copy on Front-page is Converting Poorly".

[3]: notably, document the outcome of any out-of-band conversations in the pull request.

[4]: This is usually the maintainer of a repository. For sponsored projects, it could be a project manager standing in for a client.

## Coding Conventions

To maximize readability and ease of contributing, this project follows a number of best practice conventions.

 + Must have unit tests covering > 95% of the lines of code.
 + Must be a versioned package.
 + Has a README.md file that covers the project purpose, installation, and usage.
 + Follow the [pep 0008 style guide](https://www.python.org/dev/peps/pep-0008/).
 + Package has a [pylint](http://www.pylint.org/) score of 5+.
 + If controlled via command line, a full featured CLI will be provided, such as [argparse](https://docs.python.org/2/howto/argparse.html) generates.

_Thanks to [martindale](https://github.com/martindale) for the well thought out [example CONTRIBUTING.md](https://gist.github.com/martindale/8567204)_

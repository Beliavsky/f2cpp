### f2cpp

Partial Fortran to C++ translator in Python. For example, `python xtranslate.py xvec.f90`
for `xvec.f90` having code

```fortran
module m
implicit none
contains
function mean(x) result(xmean)
real, intent(in) :: x(:)
real             :: xmean
integer          :: i, n
real             :: xsum
xsum = 0.0
n = size(x)
do i=1,n
   xsum = xsum + x(i)
end do
xmean = xsum/n
end function mean
end module m

program main
use m, only: mean
implicit none
integer, parameter :: n = 3
real :: x(n)
integer :: i
x(1) = 10.0
x(2) = 20.0
x(3) = 30.0
do i=1,n
   print*,i,10*x(i)
end do
print*,mean(x)
end program main
```

gives

```cpp
#include <iostream>
#include <cmath>
#include <vector>
using namespace std;

namespace m {
  float mean(const std::vector<float>& x) {
  float xmean;
  int i, n;
  float xsum;
  xsum = 0.0;
  n = size(x);
  for (int i = 0; i < n; ++i) {
  xsum = xsum + x[i];
  }
  xmean = xsum/n;
    return xmean;
  }
} // end namespace
int main() {
  using namespace m;
  const int n = 3;
  std::vector<float> x(n);
  int i;
  x[(1)-1] = 10.0;
  x[(2)-1] = 20.0;
  x[(3)-1] = 30.0;
  for (int i = 1; i <= n; i++) {
  cout << i << " " << 10*x[(i)-1] << endl;
  }
  cout << mean(x) << endl;
  return 0;
}
```

```fortran
! check handling of comments
! standalone comment
print*,"hello! bye!" ! inline comment
end
```
becomes

```cpp
#include <cmath>
#include <iostream>
#include <vector>
using namespace std;

int main() {
  // check handling of comments
  // standalone comment
  cout << "hello! bye!" << endl; // inline comment
  return 0;
}
```

```fortran
! math functions
real :: x
x = 3.14e0
print*, x, sin(x), cos(x), exp(x)
end
```
becomes
```cpp
#include <cmath>
#include <iostream>
#include <vector>
using namespace std;

int main() {
  // math functions
  float x;
  x = 3.14e0;
  cout << x << " " << sin(x) << " " << cos(x) << " " << exp(x) << endl;
  return 0;
}
```
```fortran
! demonstrate function, array constructor, and
! looping over array elements
module m
implicit none
contains
function factorial(n) result(nfac)
integer, intent(in) :: n
integer :: nfac
integer :: i
nfac = 1
do i=2,n
   nfac = nfac*i
end do
end function factorial
end module m

program main
use m
implicit none
integer, parameter :: n = 3, vec(n) = [3, 5, 10]
integer :: i, fac
real :: xfac
do i=1,n
   fac = factorial(vec(i))
   xfac = fac
   print*,vec(i), fac, sqrt(xfac)
   if (fac > 100) exit
end do
end program main
```
becomes
```cpp
#include <cmath>
#include <iostream>
#include <vector>
using namespace std;

// demonstrate function, array constructor, and
// looping over array elements
namespace m {
float factorial(int n) {
  int nfac;
  int i;
  nfac = 1;
  for (int i = 2; i <= n; i++) {
    nfac = nfac * i;
  }
  return nfac;
}
} // namespace m
int main() {
  using namespace m;
  const int n = 3;
  std::vector<int> vec = {3, 5, 10};
  int i, fac;
  float xfac;
  for (int i = 1; i <= n; i++) {
    fac = factorial(vec[(i)-1]);
    xfac = fac;
    cout << vec[(i)-1] << " " << fac << " " << sqrt(xfac) << endl;
    if (fac > 100)
      break;
  }
  return 0;
}
```

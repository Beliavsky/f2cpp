### f2cpp

Partial Fortran to C++ translator in Python. For example, `python xtranslate.py xvec.f90`
for `xvec.f90` being

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
// Translated C++ code:
// ---------------------
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
